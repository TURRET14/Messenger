import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence


from backend.storage import *
import backend.routers.errors
import backend.routers.dependencies
import backend.routers.parameters
from response_models import *
import backend.routers.messages.utils
import validation_service
import backend.routers.messages.validation_service


async def get_message_attachments_list(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    membership: ChatMembership

    await backend.routers.messages.validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await backend.routers.messages.validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)

    attachments_list_raw: Sequence[MessageAttachment] = ((await db.execute(
    sqlalchemy.select(MessageAttachment)
    .select_from(MessageAttachment)
    .where(MessageAttachment.message_id == selected_message.id)))
    .scalars().all())

    attachments_list: list[MessageAttachmentResponseModel] = list()

    for attachment in attachments_list_raw:
        attachments_list.append(MessageAttachmentResponseModel(id = attachment.id, chat_id = selected_chat.id, message_id = selected_message.id))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(attachments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.StreamingResponse:

    await backend.routers.messages.validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await backend.routers.messages.validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)
    await validation_service.validate_message_attachment_belonging_to_message(selected_message, selected_attachment)

    file = await minio_client.get_file(MinioBucket.messages_attachments, selected_attachment.attachment_file_path)
    file_stat = await minio_client.get_file_stat(MinioBucket.messages_attachments, selected_attachment.attachment_file_path)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def add_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    await validation_service.validate_post_message_attachment(selected_chat, selected_message, selected_user, db)

    message_attachment_name: str = await minio_client.put_file(MinioBucket.messages_attachments, file)

    new_attachment: MessageAttachment = MessageAttachment(
    message_id = selected_message.id,
    attachment_file_path = message_attachment_name)

    await db.commit()
    await db.refresh(new_attachment)

    return fastapi.responses.JSONResponse({"id": new_attachment.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validation_service.validate_post_message_attachment(selected_chat, selected_message, selected_user, db)

    await minio_client.delete_file(MinioBucket.messages_attachments, selected_attachment.attachment_file_path)

    await db.delete(selected_attachment)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_200_OK)