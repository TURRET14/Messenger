import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import (Sequence)
import datetime

from backend.routers.common_models import (IDModel)
from backend.routers.messages.response_models import LastMessageResponseModel
from backend.storage import *
from request_models import (MessageRequestModel, MessagePostRequestModel)
from response_models import (MessageResponseModel)
import backend.routers.dependencies
import backend.routers.parameters as parameters
import validation.validators as validators
import backend.routers.common_validators.validators as common_validators
import minio_deletion_service
import utils

async def get_chat_messages(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)

    messages_list_raw: Sequence[tuple[Message, bool]] = ((await db.execute(sqlalchemy.select(Message,
    sqlalchemy.case(
    (Message.sender_user_id == selected_user.id, sqlalchemy.exists(sqlalchemy.select(True).select_from(MessageReceipt).where(sqlalchemy.and_(MessageReceipt.message_id == Message.id, MessageReceipt.receiver_user_id != selected_user.id)))),
    else_= True).label("is_read"))
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id is None))
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection)))
    .tuples().all())

    messages_list: list[MessageResponseModel] = list()

    for message, is_read in messages_list_raw:
        messages_list.append(MessageResponseModel(
        id = message.id,
        chat_id = message.chat_id,
        date_and_time_sent = message.date_and_time_sent,
        date_and_time_edited = message.date_and_time_edited,
        message_text = message.message_text,
        is_read = is_read))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(messages_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_message_comments(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_chat_message_get_comments(selected_chat, selected_message, selected_user, db)

    message_comments_list_raw: Sequence[Message] = ((await db.execute(
    sqlalchemy.select(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id == selected_message.id))
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    message_comments_list: list[MessageResponseModel] = list()

    for message in message_comments_list_raw:
        message_comments_list.append(MessageResponseModel(
        id = message.id,
        chat_id = message.chat_id,
        date_and_time_sent = message.date_and_time_sent,
        date_and_time_edited = message.date_and_time_edited,
        message_text = message.message_text,
        is_read = True))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message_comments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_get_message(selected_chat, selected_message, selected_user, db)

    message_data: MessageResponseModel = MessageResponseModel(
        id = selected_message.id,
        chat_id = selected_message.chat_id,
        date_and_time_sent = selected_message.date_and_time_sent,
        date_and_time_edited = selected_message.date_and_time_edited,
        message_text = selected_message.message_text,
        is_read = await utils.is_message_read(selected_message, selected_user, db))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message_data), status_code = fastapi.status.HTTP_200_OK)


async def post_message(
    selected_chat: Chat,
    data: MessagePostRequestModel,
    file_attachments_list: list[fastapi.UploadFile],
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_post_message(selected_chat, selected_user, data.reply_message_id, data.parent_message_id, db)

    attachment_names_list: list[str] = list()
    try:
        async with db.begin():
            new_message: Message = Message(
            chat_id = selected_chat.id,
            sender_user_id = selected_user.id,
            date_and_time_sent = datetime.datetime.now(datetime.timezone.utc),
            message_text = data.message_text,
            reply_message_id = data.reply_message_id,
            parent_message_id = data.parent_message_id)

            db.add(new_message)
            await db.flush()
            await db.refresh(new_message)

            for file_attachment in file_attachments_list:
                message_attachment_name: str = await minio_client.put_file(MinioBucket.messages_attachments, file_attachment)
                attachment_names_list.append(message_attachment_name)

                new_attachment: MessageAttachment = MessageAttachment(
                message_id = new_message.id,
                attachment_file_path = message_attachment_name)

                db.add(new_attachment)
    except Exception as exc:
        await db.rollback()
        for file_attachment in attachment_names_list:
            await minio_client.delete_file(MinioBucket.messages_attachments, file_attachment)

        raise

    return fastapi.responses.JSONResponse(IDModel(id = new_message.id), status_code = fastapi.status.HTTP_201_CREATED)


async def delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_delete_message(selected_chat, selected_message, selected_user, True, db)

    attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_message_attachments_to_delete(selected_message, db)

    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    await db.delete(selected_message)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def update_message(
    selected_chat: Chat,
    selected_message: Message,
    data: MessageRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_delete_message(selected_chat, selected_message, selected_user, False, db)

    selected_message.message_text = data.message_text
    selected_message.date_and_time_edited = datetime.datetime.now(datetime.timezone.utc)

    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def search_messages_in_chat(
    offset_multiplier: int,
    message_text: str,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)

    messages_list_raw: Sequence[tuple[Message, bool]] = ((await db.execute(
    sqlalchemy.select(Message,
    sqlalchemy.case(
    (Message.sender_user_id == selected_user.id, sqlalchemy.exists(sqlalchemy.select(True).select_from(MessageReceipt).where(sqlalchemy.and_(MessageReceipt.message_id == Message.id, MessageReceipt.receiver_user_id != selected_user.id)))),
    else_= True).label("is_read"))
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id,
    Message.message_text_tsvector.op("@@")(sqlalchemy.func.websearch_to_tsquery('russian', message_text))))
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection)))
    .tuples().all())

    messages_list: list[MessageResponseModel] = list()

    for message, is_read in messages_list_raw:
        messages_list.append(MessageResponseModel(
        id = message.id,
        chat_id = message.chat_id,
        date_and_time_sent = message.date_and_time_sent,
        date_and_time_edited = message.date_and_time_edited,
        message_text = message.message_text,
        is_read = is_read))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(messages_list), status_code = fastapi.status.HTTP_200_OK)


async def search_comments_in_chat(
    offset_multiplier: int,
    message_text: str,
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_chat_message_get_comments(selected_chat, selected_message, selected_user, db)

    message_comments_list_raw: Sequence[Message] = ((await db.execute(
    sqlalchemy.select(Message)
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id == selected_message.id,
    Message.message_text_tsvector.op("@@")(sqlalchemy.func.websearch_to_tsquery('russian', message_text))))
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    message_comments_list: list[MessageResponseModel] = list()

    for message in message_comments_list_raw:
        message_comments_list.append(MessageResponseModel(
        id = message.id,
        chat_id = message.chat_id,
        date_and_time_sent = message.date_and_time_sent,
        date_and_time_edited = message.date_and_time_edited,
        message_text = message.message_text,
        is_read = True))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message_comments_list), status_code = fastapi.status.HTTP_200_OK)


async def mark_message_as_read(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_message_receipt(selected_chat, selected_message, selected_user, db)

    message_read_mark: MessageReceipt = MessageReceipt(
    message_id = selected_message.id,
    date_and_time_received = datetime.datetime.now(datetime.timezone.utc),
    receiver_user_id = selected_user.id)

    db.add(message_read_mark)

    await db.commit()
    await db.refresh(message_read_mark)

    return fastapi.responses.JSONResponse(IDModel(id = message_read_mark.id), status_code = fastapi.status.HTTP_201_CREATED)


async def get_chat_last_message(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)

    last_message_raw: Message | None = ((await db.execute(sqlalchemy.select(Message)
    .select_from(Message)
    .where(Message.chat_id == selected_chat.id)
    .order_by(Message.date_and_time_sent.desc())
    .limit(1)))
    .scalars().first())

    last_message: LastMessageResponseModel = LastMessageResponseModel()

    if last_message_raw:
        last_message.message = MessageResponseModel(
        id = last_message_raw.id,
        chat_id = last_message_raw.chat_id,
        date_and_time_sent = last_message_raw.date_and_time_sent,
        date_and_time_edited = last_message_raw.date_and_time_edited,
        message_text = last_message_raw.message_text,
        is_read = await backend.routers.messages.utils.is_message_read(last_message_raw, selected_user, db))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(last_message), status_code = fastapi.status.HTTP_200_OK)