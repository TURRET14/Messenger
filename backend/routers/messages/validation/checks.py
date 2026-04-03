import fastapi
import fastapi.encoders
import sqlalchemy.ext.asyncio

import backend.routers.messages.utils
import backend.routers.common_validators.checks as common_checks
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)

async def check_does_message_belong_to_chat(
    selected_chat: Chat,
    selected_message: Message):

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_belong_to_chat_error.error_status_code, detail = ErrorRegistry.message_does_not_belong_to_chat_error)


async def check_chat_has_comments_and_avatars(
    selected_chat: Chat):

    if selected_chat.chat_kind not in [ChatKind.CHANNEL, ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def check_chat_does_not_have_comments(
    selected_chat: Chat):

    if selected_chat.chat_kind in [ChatKind.CHANNEL, ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def check_does_chat_have_comments(
    selected_chat: Chat):

    if selected_chat.chat_kind not in [ChatKind.CHANNEL, ChatKind.PROFILE]:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_allowed_chat_type_error.error_status_code, detail = ErrorRegistry.not_allowed_chat_type_error)


async def check_message_is_root(
    selected_message: Message):

    if selected_message.parent_message_id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_have_comments_error.error_status_code, detail = ErrorRegistry.message_does_not_have_comments_error)


async def check_is_user_message_sender(
    selected_message: Message,
    selected_user: User):

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_not_message_sender_error.error_status_code, detail = ErrorRegistry.user_is_not_message_sender_error)


async def check_is_user_not_message_sender(
    selected_message: Message,
    selected_user: User):

    if selected_message.sender_user_id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.user_is_message_sender_error.error_status_code, detail = ErrorRegistry.user_is_message_sender_error)


async def check_is_message_already_marked_as_received_by_user(
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    is_message_read: bool = await backend.routers.messages.utils.is_message_read(selected_message, selected_user, db)

    if is_message_read:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_was_already_marked_as_read_error.error_status_code, detail = ErrorRegistry.message_was_already_marked_as_read_error)


async def check_is_user_allowed_to_post(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if selected_chat.chat_kind == ChatKind.PROFILE:
        if selected_chat.owner_user_id != selected_user.id:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_enough_permissions_to_post_error.error_status_code, detail = ErrorRegistry.not_enough_permissions_to_post_error)
    else:
        chat_membership: ChatMembership | None = await common_checks.check_chat_user_membership(selected_chat, selected_user, db)

        if selected_chat.chat_kind == ChatKind.CHANNEL:
            if chat_membership and chat_membership.chat_role not in [ChatRole.ADMIN, ChatRole.OWNER]:
                raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.not_enough_permissions_to_post_error.error_status_code, detail=ErrorRegistry.not_enough_permissions_to_post_error)