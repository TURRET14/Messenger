import sqlalchemy.ext.asyncio

import backend.routers.common_validators.checks as common_checks
from backend.routers.common_validators import checks
from backend.storage import *


async def validate_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_chat_user_membership(selected_chat, selected_user, db)


async def validate_get_message(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    await common_checks.check_chat_user_membership(selected_chat, selected_user, db)
    await checks.check_does_message_belong_to_chat(selected_chat, selected_message)