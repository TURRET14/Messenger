import pathlib

import fastapi
import fastapi.encoders
import minio.datatypes
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence
import urllib3

from backend.storage import *
from backend.routers.message_attachments.response_models import (MessageAttachmentResponseModel)
from backend.routers.message_attachments.validation import validators
import backend.routers.common_validators.validators as common_validators


async def get_message_attachments_list(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_get_message(selected_chat, selected_message, selected_user, db)

    attachments_list_raw: Sequence[MessageAttachment] = ((await db.execute(
    sqlalchemy.select(MessageAttachment)
    .select_from(MessageAttachment)
    .where(MessageAttachment.message_id == selected_message.id)))
    .scalars().all())

    attachments_list: list[MessageAttachmentResponseModel] = list()

    for attachment in attachments_list_raw:
        attachments_list.append(MessageAttachmentResponseModel(
        id = attachment.id,
        chat_id = selected_chat.id,
        message_id = selected_message.id,
        file_extension = pathlib.Path(attachment.attachment_file_path).suffix.lower()))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(attachments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.StreamingResponse:

    await validators.validate_get_message_attachment(selected_chat, selected_message, selected_attachment, selected_user, db)

    file: urllib3.BaseHTTPResponse = await minio_client.get_file(MinioBucket.messages_attachments, selected_attachment.attachment_file_path)
    file_stat: minio.datatypes.Object = await minio_client.get_file_stat(MinioBucket.messages_attachments, selected_attachment.attachment_file_path)

    background_tasks = fastapi.BackgroundTasks()
    background_tasks.add_task(minio_client.close_file_stream, file)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK, background = background_tasks)