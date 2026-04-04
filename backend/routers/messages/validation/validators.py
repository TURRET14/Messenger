import fastapi
import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import checks


async def validate_chat_message_get_comments(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_chat_user_membership(selected_chat, selected_user, db)
    await common_checks.check_does_message_belong_to_chat(selected_chat, selected_message)
    await checks.check_does_chat_have_comments(selected_chat)
    await checks.check_message_is_root(selected_message)


async def validate_get_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_chat_user_membership(selected_chat, selected_user, db)
    await common_checks.check_does_message_belong_to_chat(selected_chat, selected_message)


async def validate_post_message(
    selected_chat: Chat,
    selected_user: User,
    message_reply_message_id: int | None,
    message_parent_message_id: int | None,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await checks.check_is_user_allowed_to_post(selected_chat, selected_user, db)

    if message_parent_message_id:
        await checks.check_does_chat_have_comments(selected_chat)

        parent_message: Message = await common_checks.check_does_message_exist(message_parent_message_id, db)

        await checks.check_message_is_root(parent_message)

    if message_reply_message_id:
        reply_message: Message = await common_checks.check_does_message_exist(message_reply_message_id, db)

        await common_checks.check_does_message_belong_to_chat(selected_chat, reply_message)

        if message_parent_message_id != reply_message.parent_message_id:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.reply_message_belongs_to_different_parent_message_error.error_status_code, detail = ErrorRegistry.reply_message_belongs_to_different_parent_message_error)


async def validate_update_delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    is_delete: bool,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await checks.check_is_user_allowed_to_post(selected_chat, selected_user, db)

    await common_checks.check_does_message_belong_to_chat(selected_chat, selected_message)

    if is_delete:
        if selected_chat.owner_user_id != selected_user.id:
            await checks.check_is_user_message_sender(selected_message, selected_user)
    else:
        await checks.check_is_user_message_sender(selected_message, selected_user)


async def validate_message_receipt(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_chat_user_membership(selected_chat, selected_user, db)
    await common_checks.check_does_message_belong_to_chat(selected_chat, selected_message)
    await checks.check_chat_does_not_have_comments(selected_chat)
    await checks.check_is_user_not_message_sender(selected_message, selected_user)
    await checks.check_is_message_not_marked_as_received_by_user(selected_message, selected_user, db)