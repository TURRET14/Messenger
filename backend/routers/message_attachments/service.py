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
import backend.routers.messages.utils


async def get_message_attachments_list(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    membership: ChatUser

    if selected_chat.chat_kind != ChatKind.discussion:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    else:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    attachments_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    FileAttachment.id.label("message_attachment_id"),
    FileAttachment.message_id,
    sqlalchemy.literal(selected_chat.id).label("chat_id"))
    .select_from(FileAttachment)
    .where(FileAttachment.message_id == selected_message.id)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(attachments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: FileAttachment,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.StreamingResponse:

    membership: ChatUser

    if selected_chat.chat_kind != ChatKind.discussion:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    else:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
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

    membership: ChatUser

    if selected_chat.chat_kind != ChatKind.discussion:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    else:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

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

    membership: ChatUser

    if selected_chat.chat_kind != ChatKind.discussion:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    else:
        membership = await backend.routers.messages.utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id or selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    minio_client.remove_object("messages:attachments", selected_attachment.attachment_file_path)

    asyncio.run(redis_client.publish("message_attachments_delete", MessageAttachmentModel(message_attachment_id = selected_attachment.id, chat_id = selected_chat.id, message_id = selected_message.id).model_dump_json()))

    db.delete(selected_attachment)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)