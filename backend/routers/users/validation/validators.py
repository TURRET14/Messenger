import fastapi
import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
from backend.routers.users import utils
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
from backend.routers.users.validation import checks


async def validate_register(
    username: str,
    email_address: str,
    login: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await checks.check_is_username_not_taken(username, db)
    await checks.check_is_email_address_not_taken(email_address, db)
    await checks.check_is_login_not_taken(login, db)


async def validate_login(
    login: str,
    password: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> User:

    selected_user: User = await checks.check_if_user_login_exists(login, db)

    await checks.check_user_password(selected_user.password, password)

    return selected_user


async def validate_session(
    session_id: str,
    selected_user: User,
    redis_client: RedisClient) -> SessionModel:

    session_data: SessionModel = await redis_client.get_user_session_data(session_id)

    if not session_data:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_session_error.error_status_code, detail = ErrorRegistry.invalid_session_error)
    if session_data.user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_session_error.error_status_code, detail = ErrorRegistry.invalid_session_error)

    return session_data


async def validate_update_user(
    selected_user: User,
    new_username: str,
    new_email_address: str,
    new_phone_number: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if new_username != selected_user.username:
        await checks.check_is_username_not_taken(new_username, db)

    if new_email_address != selected_user.email_address:
        await checks.check_is_email_address_not_taken(new_email_address, db)

    if new_phone_number:
        new_phone_number: str
        if new_phone_number != selected_user.phone_number:
            await checks.check_is_phone_number_not_taken(new_phone_number, db)


async def validate_update_user_login(
    selected_user: User,
    new_login: str,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if new_login != selected_user.login:
        await checks.check_is_login_not_taken(new_login, db)


async def validate_update_user_password(
    hashed_password: str,
    password: str):

    await checks.check_user_password(hashed_password, password)


async def validate_user_avatar(
    avatar_photo_path: str | None) -> str:

    if not avatar_photo_path:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.avatar_not_found_error.error_status_code, detail = ErrorRegistry.avatar_not_found_error)

    return avatar_photo_path


async def validate_user_search_parameters(
    search_name: str | None,
    search_surname: str | None,
    search_second_name: str | None):

    if not search_name and not search_surname and not search_second_name:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.parameters_were_not_provided_error.error_status_code, detail = ErrorRegistry.parameters_were_not_provided_error)


async def validate_send_friend_request(
    selected_user: User,
    receiver_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_are_users_different(selected_user, receiver_user)
    await checks.check_user_friend_request_doesnt_exist(selected_user, receiver_user, db)
    await checks.check_are_users_not_friends(selected_user, receiver_user, db)
    await common_checks.check_are_users_not_blocked(selected_user, receiver_user, db)


async def validate_accept_friend_request(
    friend_request: FriendRequest,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):


    sender_user: User = await common_checks.check_is_user_found(friend_request.sender_user_id, db)
    await checks.check_is_user_friend_request_receiver(friend_request, selected_user)
    await common_checks.check_are_users_not_blocked(selected_user, sender_user, db)


async def validate_decline_friend_request(
    friend_request: FriendRequest,
    selected_user: User):

    await checks.check_is_user_friend_request_receiver(friend_request, selected_user)


async def validate_delete_sent_friend_request(
    friend_request: FriendRequest,
    selected_user: User):

    await checks.check_is_user_friend_request_sender(friend_request, selected_user)


async def validate_friendship(
    friendship: Friendship,
    selected_user: User):

    if friendship.user_id != selected_user.id and friendship.friend_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)


async def validate_is_user_not_blocked(
    selected_user: User,
    user_to_block: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_are_users_different(selected_user, user_to_block)

    if await utils.get_user_block(selected_user, user_to_block, db):
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_already_blocked_error.error_status_code, detail = ErrorRegistry.user_is_already_blocked_error)


async def validate_is_user_block_creator(
    user_block: UserBlock,
    selected_user: User):

    if user_block.user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)
