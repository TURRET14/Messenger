import fastapi
import fastapi.encoders
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.errors import (ErrorRegistry)

async def check_message_attachment_belongs_to_message(
    selected_message: Message,
    selected_attachment: MessageAttachment):

    if selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_attachment_does_not_belong_to_message_error.error_status_code, detail = ErrorRegistry.message_attachment_does_not_belong_to_message_error)