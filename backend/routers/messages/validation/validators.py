import fastapi
import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
from backend.routers.messages.request_models import MessagePostRequestModel, MessageRequestModel
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
from backend.routers.messages.validation import checks
from backend.routers.messages import utils


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
    message_data: MessagePostRequestModel,
    selected_chat: Chat,
    selected_user: User,
    attachments: list[fastapi.UploadFile],
    db: sqlalchemy.ext.asyncio.AsyncSession):

    if not message_data.message_text and not len(attachments):
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.empty_message_error.error_status_code, detail = ErrorRegistry.empty_message_error)

    await checks.check_is_user_allowed_to_post(selected_chat, selected_user, db)

    if message_data.parent_message_id:
        await checks.check_does_chat_have_comments(selected_chat)

        parent_message: Message = await common_checks.check_does_message_exist(message_data.parent_message_id, db)

        await checks.check_message_is_root(parent_message)

    if message_data.reply_message_id:
        reply_message: Message = await common_checks.check_does_message_exist(message_data.reply_message_id, db)

        await common_checks.check_does_message_belong_to_chat(selected_chat, reply_message)

        if message_data.parent_message_id != reply_message.parent_message_id:
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.reply_message_belongs_to_different_parent_message_error.error_status_code, detail = ErrorRegistry.reply_message_belongs_to_different_parent_message_error)


async def validate_update_delete_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    is_delete: bool,
    db: sqlalchemy.ext.asyncio.AsyncSession,
    message_data: MessageRequestModel | None = None):

    if not is_delete and message_data:
        if not message_data.message_text and not await utils.does_message_have_attachments(selected_message, db):
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.empty_message_error.error_status_code, detail = ErrorRegistry.empty_message_error)

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