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

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    messages_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    Message.id,
    Message.chat_id,
    Message.date_and_time_sent,
    Message.date_and_time_edited,
    Message.message_text,
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


async def post_message(
    selected_chat: Chat,
    data: MessageModel,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    new_message: Message = Message(chat_id = selected_chat.id, sender_user_id = selected_user.id, date_and_time_sent = datetime.datetime.now(datetime.timezone.utc),  message_text = data.message_text)

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    asyncio.run(redis_client.publish("messages_post", new_message.id))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_message.chat_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    asyncio.run(redis_client.publish("messages_delete", json.dumps(MessageDeleteModel(id = selected_message.id, chat_id = selected_message.chat_id))))

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

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail= backend.routers.return_details.BAD_REQUEST_ERROR)

    selected_message.message_text = data.message_text
    selected_message.date_and_time_edited = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    asyncio.run(redis_client.publish("messages_update", selected_message.id))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code=fastapi.status.HTTP_200_OK)