import fastapi
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.routers.users import utils
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

    if await utils.get_user_block(first_user, second_user, db) or await utils.get_user_block(second_user, first_user, db):
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

    friendship: Friendship | None = await utils.get_friendship(first_user, second_user, db)

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.friendship_not_found_error.error_status_code, detail = ErrorRegistry.friendship_not_found_error)

    return friendship