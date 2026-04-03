import fastapi
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.errors import (ErrorRegistry)

async def validate_are_users_not_blocked(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    block: UserBlock | None = ((await db.execute(
    sqlalchemy.select(UserBlock)
    .where(sqlalchemy.or_(
    sqlalchemy.and_(UserBlock.user_id == first_user.id, UserBlock.blocked_user_id == second_user.id),
    sqlalchemy.and_(UserBlock.user_id == second_user.id, UserBlock.blocked_user_id == first_user.id)))))
    .scalars().first())

    if block:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_blocked_error.error_status_code, detail = ErrorRegistry.user_is_blocked_error)


async def validate_are_users_friends(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    friendship: Friendship | None = (await (db.execute(sqlalchemy.select(Friendship)
    .where((sqlalchemy.and_(Friendship.user_id == min(first_user.id, second_user.id), Friendship.friend_user_id == max(first_user.id, second_user.id))))))).scalars().first()

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.users_are_not_friends_error.error_status_code, detail = ErrorRegistry.users_are_not_friends_error)