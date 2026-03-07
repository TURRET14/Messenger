import fastapi
import fastapi.encoders
import redis
import sqlalchemy.orm
import json
import asyncio
from typing import Sequence

from backend.storage import *
from models import *
import backend.routers.return_details
import backend.routers.dependencies
import backend.routers.parameters
import utils

async def get_chat_messages(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    membership: ChatUser | None = None

    if selected_chat.chat_kind in [ChatKind.private, ChatKind.group, ChatKind.community]:
        membership = await utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    elif selected_chat.chat_kind == ChatKind.discussion:
        membership = await utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if selected_chat.chat_kind != ChatKind.wall and not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    messages_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    Message.id,
    Message.chat_id,
    Message.date_and_time_sent,
    Message.date_and_time_edited,
    Message.message_text,
    Message.reply_message_id,
    User.id.label("sender_id"),
    User.username.label("sender_username"),
    User.name.label("sender_name"),
    User.surname.label("sender_surname"),
    User.second_name.label("sender_second_name"))
    .select_from(Message)
    .where(Message.chat_id == selected_chat.id)
    .join(User, User.id == Message.sender_user_id)
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(messages_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_message_by_id(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    membership: ChatUser | None = None

    if selected_chat.chat_kind in [ChatKind.private, ChatKind.group, ChatKind.community]:
        membership = await utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    elif selected_chat.chat_kind == ChatKind.discussion:
        membership = await utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if selected_chat.chat_kind != ChatKind.wall and not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    message: MessageResponseModel = MessageResponseModel(
        id = selected_message.id,
        chat_id = selected_message.id,
        date_and_time_sent = selected_message.date_and_time_sent,
        date_and_time_edited = selected_message.date_and_time_edited,
        message_text = selected_message.message_text,
        sender_id = selected_user.id,
        sender_username = selected_user.username,
        sender_name = selected_user.name,
        sender_surname = selected_user.surname,
        sender_second_name = selected_user.second_name,
        reply_message_id = selected_message.reply_message_id
    )

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message), status_code = fastapi.status.HTTP_200_OK)

async def post_message(
    selected_chat: Chat,
    data: MessageModel,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    membership: ChatUser | None = None

    if selected_chat.chat_kind in [ChatKind.private, ChatKind.group, ChatKind.community]:
        membership = await utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    elif selected_chat.chat_kind == ChatKind.discussion:
        membership = await utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if selected_chat.chat_kind != ChatKind.wall and not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if data.reply_message_id and not db.execute(sqlalchemy.select(Message).where(sqlalchemy.and_(Message.id == data.reply_message_id, Message.chat_id == selected_chat.id))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)
    elif selected_chat.chat_kind == ChatKind.wall and selected_chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    new_message: Message = Message(chat_id = selected_chat.id, sender_user_id = selected_user.id, date_and_time_sent = datetime.datetime.now(datetime.timezone.utc),  message_text = data.message_text, reply_message_id = data.reply_message_id)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    if selected_chat.chat_kind == ChatKind.community:
        new_discussion: Chat = Chat(chat_kind = ChatKind.discussion, date_and_time_created = datetime.datetime.now(datetime.timezone.utc), discussion_message_id = new_message.id)
        db.add(new_discussion)
        db.commit()

    asyncio.create_task(redis_client.publish("messages_post", new_message.id))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    membership: ChatUser | None = None

    if selected_chat.chat_kind in [ChatKind.private, ChatKind.group, ChatKind.community]:
        membership = await utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    elif selected_chat.chat_kind == ChatKind.discussion:
        membership = await utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if selected_chat.chat_kind != ChatKind.wall and not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_message.chat_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)
    elif selected_chat.chat_kind == ChatKind.wall and selected_chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    asyncio.create_task(redis_client.publish("messages_delete", json.dumps(MessageDeleteModel(id = selected_message.id, chat_id = selected_message.chat_id))))

    db.delete(selected_message)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code=fastapi.status.HTTP_200_OK)


async def update_message(
    selected_chat: Chat,
    selected_message: Message,
    data: MessageModel,
    selected_user: User,
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    membership: ChatUser | None = None

    if selected_chat.chat_kind in [ChatKind.private, ChatKind.group, ChatKind.community]:
        membership = await utils.get_chat_active_user_membership(selected_chat, selected_user, db)
    elif selected_chat.chat_kind == ChatKind.discussion:
        membership = await utils.get_chat_active_user_membership(db.execute(sqlalchemy.select(Chat).select_from(Message).where(Message.id == selected_chat.discussion_message_id).join(Chat, Chat.id == Message.chat_id)).scalars().first(), selected_user, db)

    if selected_chat.chat_kind != ChatKind.wall and not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if data.reply_message_id and not db.execute(sqlalchemy.select(Message).where(sqlalchemy.and_(Message.id == data.reply_message_id, Message.chat_id == selected_chat.id))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_chat.chat_kind == ChatKind.community and membership.chat_role not in [ChatRole.admin, ChatRole.owner]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)
    elif selected_chat.chat_kind == ChatKind.wall and selected_chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    selected_message.message_text = data.message_text
    selected_message.date_and_time_edited = datetime.datetime.now(datetime.timezone.utc)
    selected_message.reply_message_id = data.reply_message_id
    db.commit()

    asyncio.create_task(redis_client.publish("messages_update", selected_message.id))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def search_messages_in_chat(
    offset_multiplier: int,
    message_text: str,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_active_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    messages_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    Message.id,
    Message.chat_id,
    Message.date_and_time_sent,
    Message.date_and_time_edited,
    Message.message_text,
    Message.reply_message_id,
    User.id.label("sender_id"),
    User.username.label("sender_username"),
    User.name.label("sender_name"),
    User.surname.label("sender_surname"),
    User.second_name.label("sender_second_name"))
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id,
    Message.message_text_tsvector.op("@@")(sqlalchemy.func.plainto_tsquery('russian', message_text))))
    .join(User, User.id == Message.sender_user_id)
    .order_by(Message.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(messages_list), status_code = fastapi.status.HTTP_200_OK)