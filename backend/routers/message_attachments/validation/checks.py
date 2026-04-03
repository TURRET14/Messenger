import fastapi
import fastapi.encoders
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
import backend.routers.messages.validation.checks as message_checks

async def check_message_attachment_belongs_to_message(
    selected_message: Message,
    selected_attachment: MessageAttachment):

    if selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_attachment_does_not_belong_to_message_error.error_status_code, detail = ErrorRegistry.message_attachment_does_not_belong_to_message_error)



async def validate_post_message_attachment(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await message_checks.check_is_user_allowed_to_post(selected_chat, selected_user, db)

    await message_checks.check_does_message_belong_to_chat(selected_chat, selected_message)

    await message_checks.check_is_user_message_sender(selected_message, selected_user)