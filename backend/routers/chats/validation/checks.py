import fastapi
import sqlalchemy.ext.asyncio
from backend.routers.errors import (ErrorRegistry)
from backend.storage import *
import backend.routers.chats.utils as utils
import backend.routers.common_validators.validators as common_validators

async def check_avatar_photo_path(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> str:

    if selected_chat.chat_kind in [ChatKind.GROUP, ChatKind.CHANNEL]:
        if not selected_chat.avatar_photo_path:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.avatar_not_found_error.error_status_code, detail = ErrorRegistry.avatar_not_found_error)
        else:
            return selected_chat.avatar_photo_path
    elif selected_chat.chat_kind in [ChatKind.PRIVATE]:
        other_user: User | None = await utils.get_other_chat_user(selected_chat, selected_user, db)
        if not other_user:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_not_found_error.error_status_code, detail = ErrorRegistry.user_not_found_error)
        if not other_user.avatar_photo_path:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.avatar_not_found_error.error_status_code, detail = ErrorRegistry.avatar_not_found_error)
        else:
            return other_user.avatar_photo_path
    elif selected_chat.chat_kind in [ChatKind.PROFILE]:
        chat_owner: User | None = (await db.execute(sqlalchemy.select(User).select_from(User).where(User.id == selected_chat.owner_user_id))).scalars().first()
        if not chat_owner:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_not_found_error.error_status_code, detail = ErrorRegistry.user_not_found_error)
        if not chat_owner.avatar_photo_path:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.avatar_not_found_error.error_status_code, detail = ErrorRegistry.avatar_not_found_error)
        else:
            return chat_owner.avatar_photo_path
    else:
        return str()


async def check_users_dont_have_private_chat(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if await utils.get_users_private_chat(first_user, second_user, db):
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.private_chat_already_exists_error.error_status_code, detail = ErrorRegistry.private_chat_already_exists_error)


async def check_chat_has_avatar_and_name_and_owner(
    selected_chat: Chat):

    if selected_chat.chat_kind not in [ChatKind.GROUP, ChatKind.CHANNEL]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def check_is_chat_user_owner_or_admin(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    chat_membership: ChatMembership | None = (await db.execute(sqlalchemy.select(ChatMembership).where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat.id, ChatMembership.chat_user_id == selected_user.id)))).scalars().first()

    if chat_membership and chat_membership.chat_role not in [ChatRole.ADMIN, ChatRole.OWNER]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)


async def check_is_chat_user_owner(
    selected_chat: Chat,
    selected_user: User):

    if selected_chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)


async def check_is_chat_user_not_admin(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    chat_membership: ChatMembership = await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    if chat_membership.chat_role == ChatRole.ADMIN:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_already_admin_error.error_status_code, detail = ErrorRegistry.user_is_already_admin_error)


async def check_is_chat_user_admin(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    chat_membership: ChatMembership = await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    if chat_membership.chat_role != ChatRole.ADMIN:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_not_admin_error.error_status_code, detail = ErrorRegistry.user_is_not_admin_error)


async def check_does_chat_membership_belong_to_chat(
    selected_chat: Chat,
    chat_membership: ChatMembership):

    if chat_membership.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)