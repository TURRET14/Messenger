"""
Общая утилита для отдачи медиа-файлов из MinIO с поддержкой HTTP Range Requests.

Без Range support тег <video> в браузере вынужден скачивать весь файл до начала
воспроизведения и не умеет перематывать. С поддержкой 206 Partial Content
браузер сам качает только нужные сегменты по мере воспроизведения/перемотки.

MinIO нативно поддерживает range-чтение объектов через get_object(offset, length),
поэтому мы не нагружаем сервер «прокачиванием» всего файла.
"""

import re
from typing import AsyncIterator

import fastapi
import minio.datatypes

from backend.storage.minio_handler import MinioBucket, MinioClient


_RANGE_RE = re.compile(r"^bytes=(\d+)?-(\d+)?$")
_DEFAULT_CHUNK_SIZE = 1024 * 64  # 64 KiB

# Cache-Control по типам контента: для изображений (аватары) более короткий
# срок, чтобы при смене фото не пришлось ждать TTL; вложения сообщений
# не меняются после загрузки, поэтому могут кешироваться дольше.
_CACHE_CONTROL_AVATAR = "private, max-age=300"
_CACHE_CONTROL_ATTACHMENT = "private, max-age=86400, immutable"


def _cache_control_for(bucket: MinioBucket) -> str:
    if bucket == MinioBucket.messages_attachments:
        return _CACHE_CONTROL_ATTACHMENT
    return _CACHE_CONTROL_AVATAR


def _parse_range(header: str | None, total_size: int) -> tuple[int, int] | None:
    """Парсит Range-заголовок типа `bytes=START-END`. Возвращает (start, end)
    включительно. Если Range отсутствует, недопустим или выходит за границы —
    возвращает None (тогда отдаётся весь объект 200 OK)."""
    if not header:
        return None
    match = _RANGE_RE.match(header.strip())
    if not match:
        return None
    raw_start, raw_end = match.group(1), match.group(2)

    if raw_start is None and raw_end is None:
        return None

    if raw_start is None:
        # bytes=-N — последние N байт
        suffix_length = int(raw_end or "0")
        if suffix_length <= 0:
            return None
        start = max(0, total_size - suffix_length)
        end = total_size - 1
    else:
        start = int(raw_start)
        if raw_end is None or raw_end == "":
            end = total_size - 1
        else:
            end = min(int(raw_end), total_size - 1)

    if start < 0 or start >= total_size or end < start:
        return None

    return start, end


async def _stream_response_body(file, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> AsyncIterator[bytes]:
    """Оборачивает синхронный urllib3-стрим из MinIO в async-итератор для
    StreamingResponse. Гарантирует освобождение соединения по завершении."""
    try:
        for chunk in file.stream(chunk_size):
            yield chunk
    finally:
        try:
            file.close()
        except Exception:
            pass
        try:
            file.release_conn()
        except Exception:
            pass


async def serve_minio_file(
    request: fastapi.Request,
    bucket: MinioBucket,
    object_name: str,
    minio_client: MinioClient,
) -> fastapi.responses.StreamingResponse:
    """Возвращает HTTP-ответ с медиа-файлом из MinIO. Поддерживает:
    - HTTP Range (RFC 7233) → 206 Partial Content для частичного чтения;
    - Заголовок Accept-Ranges: bytes — браузер видит, что range поддержан;
    - Условные запросы If-None-Match → 304 Not Modified через ETag;
    - Cache-Control с разумным TTL по типу bucket.

    Заголовок ETag и точный размер берутся из stat объекта в MinIO."""

    file_stat: minio.datatypes.Object = await minio_client.get_file_stat(bucket, object_name)
    total_size: int = int(file_stat.size or 0)
    content_type: str = file_stat.content_type or "application/octet-stream"
    etag: str | None = file_stat.etag
    cache_control = _cache_control_for(bucket)

    # If-None-Match: сравниваем ETag и возвращаем 304 без тела при совпадении.
    if etag:
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag.strip('"'):
            headers = {
                "ETag": f'"{etag.strip(chr(34))}"',
                "Cache-Control": cache_control,
                "Accept-Ranges": "bytes",
            }
            return fastapi.responses.Response(status_code = 304, headers = headers)

    range_header = request.headers.get("range")
    parsed = _parse_range(range_header, total_size) if total_size > 0 else None

    base_headers: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Cache-Control": cache_control,
        "Content-Disposition": "inline",
    }
    if etag:
        base_headers["ETag"] = f'"{etag}"'

    if parsed is None:
        # Полное содержимое — 200 OK со streaming-телом.
        file = await minio_client.get_file(bucket, object_name)
        headers = {
            **base_headers,
            "Content-Length": str(total_size) if total_size > 0 else "",
        }
        # Удаляем пустые заголовки (если размер неизвестен — не выставляем).
        headers = {k: v for k, v in headers.items() if v}
        return fastapi.responses.StreamingResponse(
            _stream_response_body(file),
            media_type = content_type,
            headers = headers,
            status_code = fastapi.status.HTTP_200_OK,
        )

    # 206 Partial Content — читаем только нужный диапазон из MinIO.
    start, end = parsed
    length = end - start + 1
    file = await minio_client.get_file_range(bucket, object_name, start, length)
    headers = {
        **base_headers,
        "Content-Range": f"bytes {start}-{end}/{total_size}",
        "Content-Length": str(length),
    }
    return fastapi.responses.StreamingResponse(
        _stream_response_body(file),
        media_type = content_type,
        headers = headers,
        status_code = fastapi.status.HTTP_206_PARTIAL_CONTENT,
    )
