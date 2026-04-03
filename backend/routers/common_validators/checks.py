import fastapi
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

import backend.routers.users.utils
import backend.routers.chats.utils
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)


async def check_are_users_different(
    first_user: User,
    second_user: User):

    if first_user.id == second_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.selected_user_is_request_sender_error.error_status_code, detail = ErrorRegistry.selected_user_is_request_sender_error)


async def check_users_are_not_blocked(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if await backend.routers.users.utils.get_user_block(first_user, second_user, db) or await backend.routers.users.utils.get_user_block(second_user, first_user, db):
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_blocked_error.error_status_code, detail = ErrorRegistry.user_is_blocked_error)


async def check_is_user_found(
    selected_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> User:

    selected_user: User | None = (((await db.execute(
    sqlalchemy.select(User)
    .where(User.id == selected_user_id))))
    .scalars().first())

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_not_found_error.error_status_code, detail = ErrorRegistry.user_not_found_error)

    return selected_user


async def check_users_friendship(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Friendship:

    friendship: Friendship | None = await backend.routers.users.utils.get_friendship(first_user, second_user, db)

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.friendship_not_found_error.error_status_code, detail = ErrorRegistry.friendship_not_found_error)

    return friendship


async def check_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership | None:

    chat_membership: ChatMembership | None = await backend.routers.chats.utils.get_chat_user_membership(selected_chat, selected_user, db)

    if not chat_membership:
        if selected_chat.chat_kind != ChatKind.PROFILE:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_membership_not_found_error.error_status_code, detail = ErrorRegistry.chat_membership_not_found_error)

    return chat_membership


async def check_does_message_exist(
    selected_message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Message:

    selected_message: Message | None = ((await db.execute(
    sqlalchemy.select(Message)
    .where(Message.id == selected_message_id)))
    .scalars().first())

    if not selected_message:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_not_found_error.error_status_code, detail = ErrorRegistry.message_not_found_error)

    return selected_message