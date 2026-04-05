import sqlalchemy.ext.asyncio

import backend.routers.common_validators.validators as common_validators
from backend.storage import *
from backend.routers.message_attachments.validation import checks


async def validate_get_message_attachment(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: MessageAttachment,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_validators.validate_get_message(selected_chat, selected_message, selected_user, db)
    await checks.check_message_attachment_belongs_to_message(selected_message, selected_attachment)