from datetime import datetime

import fastapi
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.routers.common_models import *
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
from backend.storage.redis_handler import SessionModel


async def get_session_user(
    session_id: str = fastapi.Cookie(),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> User:

    session: SessionModel | None = await redis_client.get_user_session_data(session_id)
    if session:
        if session.expiration_datetime > int(datetime.now().timestamp()):
            session_user = (await db.execute(sqlalchemy.select(User).where(User.id == session.user_id))).scalars().first()
            if session_user:
                return session_user
            else:
                raise fastapi.HTTPException(status_code = ErrorRegistry.unauthorized_error.error_status_code, detail = ErrorRegistry.unauthorized_error)
        else:
            raise fastapi.HTTPException(status_code = ErrorRegistry.unauthorized_error.error_status_code, detail = ErrorRegistry.unauthorized_error)
    else:
        raise fastapi.HTTPException(status_code = ErrorRegistry.unauthorized_error.error_status_code, detail = ErrorRegistry.unauthorized_error)


async def get_user_by_path_user_id(
    user_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> User:

    selected_user: User = (await db.execute(sqlalchemy.select(User).where(User.id == user_id))).scalars().first()

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_not_found_error.error_status_code, detail = ErrorRegistry.user_not_found_error)
    else:
        return selected_user


async def get_user_by_data_id(
    user_id_model: IDModel = fastapi.Body(),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> User:

    selected_user: User = (await db.execute(sqlalchemy.select(User).where(User.id == user_id_model.id))).scalars().first()

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_not_found_error.error_status_code, detail = ErrorRegistry.user_not_found_error)
    else:
        return selected_user


async def get_chat_by_path_id(
    chat_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> Chat:

    selected_chat: Chat = (await db.execute(sqlalchemy.select(Chat).where(Chat.id == chat_id))).scalars().first()

    if not selected_chat:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_not_found_error.error_status_code, detail = ErrorRegistry.chat_not_found_error)
    else:
        return selected_chat


async def get_message_by_path_id(
    message_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> Message:

    selected_message: Message = (await db.execute(sqlalchemy.select(Message).where(Message.id == message_id))).scalars().first()

    if not selected_message:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_not_found_error.error_status_code, detail = ErrorRegistry.message_not_found_error)
    else:
        return selected_message


async def get_message_attachment_by_id(
    attachment_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> MessageAttachment:

    selected_attachment: MessageAttachment = (await db.execute(sqlalchemy.select(MessageAttachment).where(MessageAttachment.id == attachment_id))).scalars().first()

    if not selected_attachment:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_attachment_not_found_error.error_status_code, detail = ErrorRegistry.message_attachment_not_found_error)
    else:
        return selected_attachment


async def get_chat_membership_by_path_id(
    chat_membership_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> ChatMembership:

    chat_membership: ChatMembership = (await db.execute(sqlalchemy.select(ChatMembership).where(ChatMembership.id == chat_membership_id))).scalars().first()

    if not chat_membership:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_membership_not_found_error.error_status_code, detail = ErrorRegistry.chat_membership_not_found_error)
    else:
        return chat_membership


async def get_friend_request_by_path_id(
    friend_request_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> FriendRequest:

    friend_request: FriendRequest = (await db.execute(sqlalchemy.select(FriendRequest).where(FriendRequest.id == friend_request_id))).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.friend_request_not_found_error.error_status_code, detail = ErrorRegistry.friend_request_not_found_error)
    else:
        return friend_request