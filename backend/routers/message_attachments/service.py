import json

import fastapi
import fastapi.encoders
import redis
import sqlalchemy.orm
import minio
import pathlib
import uuid
import io
import asyncio
from typing import Sequence


from backend.storage import *
import backend.routers.return_details
import backend.routers.dependencies
import backend.routers.parameters
from models import *


async def get_message_attachments_list(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    attachments_list: Sequence[FileAttachment] = db.execute(sqlalchemy.select(FileAttachment)
    .where(FileAttachment.message_id == selected_message.id)).scalars().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(attachments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: FileAttachment,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.StreamingResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id or selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    file = minio_client.get_object("messages:attachments", selected_attachment.attachment_file_path)
    file_stat = minio_client.stat_object("messages:attachments", selected_attachment.attachment_file_path)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def add_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: minio.Minio,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if file.size > backend.routers.parameters.max_attachment_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_SIZE_TOO_LARGE_ERROR)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    #MinIO - Загрузка аватара
    minio_file_name: str = f"messages/{selected_message.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("messages:attachments", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)


    new_attachment: FileAttachment = FileAttachment(
    message_id = selected_message.id,
    attachment_file_path = minio_file_name)
    db.commit()
    db.refresh(new_attachment)

    asyncio.run(redis_client.publish("message_attachments_post", MessageAttachmentModel(message_attachment_id = new_attachment.id, chat_id = selected_chat.id, message_id = selected_message.id).model_dump_json()))

    return fastapi.responses.JSONResponse({"id": new_attachment.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: FileAttachment,
    selected_user: User,
    minio_client: minio.Minio,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id or selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    minio_client.remove_object("messages:attachments", selected_attachment.attachment_file_path)

    asyncio.run(redis_client.publish("message_attachments_delete", MessageAttachmentModel(message_attachment_id = selected_attachment.id, chat_id = selected_chat.id, message_id = selected_message.id).model_dump_json()))

    db.delete(selected_attachment)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)