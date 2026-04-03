import fastapi
import sqlalchemy.orm
import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
import backend.routers.common_validators.validators as common_validators
import backend.routers.messages.validation.validators as messages_validators
import backend.routers.messages.validation.checks as messages_checks
import backend.routers.chats.utils
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import checks


async def validate_get_message_attachment(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_get_message(selected_chat, selected_message, selected_user, db)
    await checks.check_message_attachment_belongs_to_message(selected_message, selected_attachment)


async def validate_add_message_attachment(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await messages_checks.check_does_message_belong_to_chat(selected_chat, selected_message)
    await messages_checks.check_is_user_allowed_to_post(selected_chat, selected_user, db)


async def validate_delete_message_attachment(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await checks.check_message_attachment_belongs_to_message(selected_message, selected_attachment)
    await messages_validators.validate_update_delete_message(selected_chat, selected_message, selected_user, True, db)