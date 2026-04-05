import fastapi
import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
import backend.routers.common_validators.validators as common_validators
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import backend.routers.chats.validation.checks as checks
import backend.routers.chats.utils as utils

async def validate_get_chat_avatar(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> str:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    avatar_photo_path: str = await checks.check_avatar_photo_path(selected_chat, selected_user, db)

    return avatar_photo_path


async def validate_create_private_chat(
    selected_user: User,
    other_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_are_users_not_blocked(selected_user, other_user, db)
    await checks.check_users_dont_have_private_chat(selected_user, other_user, db)


async def validate_update_avatar_or_name(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_chat_has_avatar_and_name_and_owner(selected_chat)
    await checks.check_is_chat_user_owner_or_admin(selected_chat, selected_user, db)


async def validate_update_chat_owner_and_add_admin(
    selected_chat: Chat,
    selected_user: User,
    new_owner_or_admin_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_chat_has_avatar_and_name_and_owner(selected_chat)
    await common_checks.check_are_users_different(selected_user, new_owner_or_admin_user)
    await checks.check_is_chat_user_owner(selected_chat, selected_user)

    new_owner_or_admin_user_membership: ChatMembership = await common_validators.validate_chat_user_membership(selected_chat, new_owner_or_admin_user, db)

    return new_owner_or_admin_user_membership


async def validate_delete_chat_admin(
    selected_chat: Chat,
    selected_user: User,
    admin_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership:

    admin_membership: ChatMembership = await validate_update_chat_owner_and_add_admin(selected_chat, selected_user, admin_user, db)

    await checks.check_is_chat_user_admin(selected_chat, selected_user, db)

    return admin_membership


async def validate_add_user(
    selected_chat: Chat,
    selected_user: User,
    new_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_chat_has_avatar_and_name_and_owner(selected_chat)
    await common_checks.check_are_users_different(selected_user, new_user)
    await common_checks.check_users_friendship(selected_user, new_user, db)


async def validate_delete_user(
    selected_chat: Chat,
    selected_user: User,
    chat_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_chat_has_avatar_and_name_and_owner(selected_chat)
    await common_checks.check_are_users_different(selected_user, chat_user)
    await checks.check_is_chat_user_owner_or_admin(selected_chat, selected_user, db)

    chat_user_membership: ChatMembership | None = await common_checks.check_chat_user_membership(selected_chat, chat_user, db)

    if not chat_user_membership:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_membership_not_found_error.error_status_code, detail = ErrorRegistry.chat_membership_not_found_error)

    return chat_user_membership


async def validate_leave_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership:

    if selected_chat.chat_kind in [ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)

    selected_user_chat_membership: ChatMembership | None = await common_checks.check_chat_user_membership(selected_chat, selected_user, db)

    if not selected_user_chat_membership:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.chat_membership_not_found_error.error_status_code, detail = ErrorRegistry.chat_membership_not_found_error)

    if selected_chat.owner_user_id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.owner_cannot_leave_chat_error.error_status_code, detail = ErrorRegistry.owner_cannot_leave_chat_error)

    return selected_user_chat_membership


async def validate_delete_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_chat_has_avatar_and_name_and_owner(selected_chat)
    await checks.check_is_chat_user_owner(selected_chat, selected_user)


async def validate_get_chat_membership(
    selected_chat: Chat,
    chat_membership: ChatMembership,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_does_chat_membership_belong_to_chat(selected_chat, chat_membership)


async def validate_get_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> str:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)

    chat_name: str | None = await utils.get_chat_name(selected_chat, selected_user, db)
    if not chat_name:
        chat_name: str = str()

    return chat_name