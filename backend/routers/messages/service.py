import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import (Sequence)
import datetime

from backend.storage import *
from request_models import (MessageRequestModel, MessagePostRequestModel)
from response_models import (MessageResponseModel)
from backend.routers.errors import (ErrorRegistry)
import backend.routers.dependencies
import backend.routers.parameters as parameters
import validation_service
import utils

async def get_chat_messages(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)

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

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)
    await validation_service.validate_chat_has_comments(selected_chat)
    await validation_service.validate_message_is_root(selected_message)

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


async def get_chat_message_by_id(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)

    message_data: MessageResponseModel = MessageResponseModel(
        id = selected_message.id,
        chat_id = selected_message.chat_id,
        date_and_time_sent = selected_message.date_and_time_sent,
        date_and_time_edited = selected_message.date_and_time_edited,
        message_text = selected_message.message_text,
        is_read = await utils.is_message_read(selected_message.id, db))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message_data), status_code = fastapi.status.HTTP_200_OK)

async def post_message(
    selected_chat: Chat,
    data: MessagePostRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validation_service.validate_post_message(selected_chat, selected_user, data.reply_message_id, data.parent_message_id, db)

    new_message: Message = Message(
    chat_id = selected_chat.id,
    sender_user_id = selected_user.id,
    date_and_time_sent = datetime.datetime.now(datetime.timezone.utc),
    message_text = data.message_text,
    reply_message_id = data.reply_message_id,
    parent_message_id = data.parent_message_id)

    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    return fastapi.responses.JSONResponse({"id": new_message.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validation_service.validate_update_delete_message(selected_chat, selected_message, selected_user, True, db)

    attachments_to_delete: list[BucketWithFiles] = list()
    files_list: Sequence[str] = ((await db.execute(
    sqlalchemy.select(MessageAttachment.attachment_file_path)
    .select_from(MessageAttachment)
    .where(sqlalchemy.or_(MessageAttachment.message_id == selected_message.id,
    MessageAttachment.message_id.in_(sqlalchemy.select(Message.id).select_from(Message).where(Message.parent_message_id == selected_message.id))))))
    .scalars().all())

    attachments_to_delete.append(BucketWithFiles(MinioBucket.messages_attachments, list(files_list)))

    await db.delete(selected_message)
    await db.commit()

    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def update_message(
    selected_chat: Chat,
    selected_message: Message,
    data: MessageRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validation_service.validate_update_delete_message(selected_chat, selected_message, selected_user, False, db)

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

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)

    messages_list_raw: Sequence[tuple[Message, bool]] = ((await db.execute(
    sqlalchemy.select(Message,
    sqlalchemy.case(
    (Message.sender_user_id == selected_user.id, sqlalchemy.exists(sqlalchemy.select(True).select_from(MessageReceipt).where(sqlalchemy.and_(MessageReceipt.message_id == Message.id, MessageReceipt.receiver_user_id != selected_user.id)))),
    else_= True).label("is_read"))
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id,
    Message.message_text_tsvector.op("@@")(sqlalchemy.func.plainto_tsquery('russian', message_text))))
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

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)
    await validation_service.validate_chat_has_comments(selected_chat)
    await validation_service.validate_message_is_root(selected_message)

    message_comments_list_raw: Sequence[Message] = ((await db.execute(
    sqlalchemy.select(Message)
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id == selected_message.id,
    Message.message_text_tsvector.op("@@")(sqlalchemy.func.plainto_tsquery('russian', message_text))))
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

    await validation_service.validate_chat_user_membership(selected_chat, selected_user, db)
    await validation_service.validate_message_belonging_to_chat(selected_chat, selected_message)
    await validation_service.validate_chat_does_not_have_comments(selected_chat)
    await validation_service.validate_is_user_not_message_sender(selected_message, selected_user)
    await validation_service.validate_is_message_already_marked_as_received(selected_message, selected_user, db)

    message_read_mark: MessageReceipt = MessageReceipt(
    message_id = selected_message.id,
    date_and_time_received = datetime.datetime.now(datetime.timezone.utc),
    receiver_user_id = selected_user.id)

    db.add(message_read_mark)
    await db.commit()
    await db.refresh(message_read_mark)

    return fastapi.responses.JSONResponse({"id": message_read_mark.id}, status_code = fastapi.status.HTTP_200_OK)