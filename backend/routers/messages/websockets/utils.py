import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from backend.storage import *
from typing import Sequence

async def get_chat_user_ids(
    selected_chat_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Sequence[int]:

    message_receivers_ids_list: Sequence[int] = ((await db.execute(
    sqlalchemy.select(User.id)
    .select_from(ChatMembership)
    .where(ChatMembership.chat_id == selected_chat_id)
    .join(User, User.id == ChatMembership.chat_user_id)))
    .scalars().all())

    return message_receivers_ids_list