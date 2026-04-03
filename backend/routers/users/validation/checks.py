import fastapi
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.routers.users import utils
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import backend.routers.security as security

async def check_is_username_not_taken(
    username: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if (await db.execute(sqlalchemy.select(User).where(User.username == username))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.username_already_taken_error.error_status_code, detail = ErrorRegistry.username_already_taken_error)


async def check_is_login_not_taken(
    login: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if (await db.execute(sqlalchemy.select(User).where(User.login == login))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.login_already_taken_error.error_status_code, detail = ErrorRegistry.login_already_taken_error)


async def check_is_email_address_not_taken(
    email_address: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if (await db.execute(sqlalchemy.select(User).where(User.email_address == email_address))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.email_already_taken_error.error_status_code, detail = ErrorRegistry.email_already_taken_error)


async def check_is_phone_number_not_taken(
    phone_number: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if (await db.execute(sqlalchemy.select(User).where(User.phone_number == phone_number))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.phone_number_already_taken_error.error_status_code, detail = ErrorRegistry.phone_number_already_taken_error)

async def check_if_user_login_exists(
    login: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> User:

    selected_user: User | None = ((await (db.execute(
    sqlalchemy.select(User)
    .where(User.login == login))))
    .scalars().first())

    if not selected_user:
        raise fastapi.HTTPException(status_code = ErrorRegistry.incorrect_login_error.error_status_code, detail = ErrorRegistry.incorrect_login_error)

    return selected_user


async def check_user_agent(
    user_agent: str | None) -> str:

    if not user_agent:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.bad_request_error.error_status_code, detail = ErrorRegistry.bad_request_error)

    return user_agent


async def check_user_password(
    hashed_password: str,
    password: str):

    if not await security.verify_password(hashed_password, password):
        raise fastapi.exceptions.HTTPException(ErrorRegistry.incorrect_password_error.error_status_code, ErrorRegistry.incorrect_password_error)


async def check_user_friend_request_doesnt_exist(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if await utils.get_friend_request(first_user, second_user, db) or await utils.get_friend_request(second_user, first_user, db):
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.friend_request_already_exists_error.error_status_code, detail = ErrorRegistry.friend_request_already_exists_error)


async def check_are_users_not_friends(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    friendship: Friendship | None = await utils.get_friendship(first_user, second_user, db)

    if friendship:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.users_are_already_friends_error.error_status_code, detail = ErrorRegistry.users_are_already_friends_error)


async def check_is_user_friend_request_receiver(
    friend_request: FriendRequest,
    selected_user: User):

    if friend_request.receiver_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)


async def check_is_user_friend_request_sender(
    friend_request: FriendRequest,
    selected_user: User):

    if friend_request.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)