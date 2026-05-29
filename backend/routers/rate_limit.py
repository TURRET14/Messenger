import fastapi

from backend.routers.errors import ErrorRegistry
from backend.storage import redis_handler
from backend.storage.redis_handler import RedisClient


def _client_ip(request: fastapi.Request) -> str:
    """IP клиента. За обратным прокси (Caddy) uvicorn запускается с
    --proxy-headers, поэтому request.client.host уже содержит реальный
    адрес из X-Forwarded-For, а не адрес прокси."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limiter(bucket: str, limit: int, window_seconds: int):
    """Фабрика FastAPI-зависимостей для ограничения частоты запросов по IP.

    Применяется к чувствительным эндпоинтам (вход, регистрация, сброс
    пароля, ввод кодов подтверждения), чтобы исключить брутфорс 6-значных
    кодов и перебор паролей.
    """

    async def dependency(
        request: fastapi.Request,
        redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client),
    ) -> None:
        key = f"{bucket}:{_client_ip(request)}"
        allowed = await redis_client.rate_limit_hit(key, limit, window_seconds)
        if not allowed:
            raise fastapi.exceptions.HTTPException(
                status_code = ErrorRegistry.too_many_requests_error.error_status_code,
                detail = ErrorRegistry.too_many_requests_error,
            )

    return dependency
