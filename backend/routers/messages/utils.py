import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *

async def get_chat_user_membership(
    selected_chat_id: int,
    selected_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership | None:

    chat_membership: ChatMembership | None = ((await db.execute(
    sqlalchemy.select(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat_id, ChatMembership.chat_user_id == selected_user_id))))
    .scalars().first())

    return chat_membership


async def is_message_read(
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if selected_message.sender_user_id == selected_user.id:
        return True
    else:
        message_receipt: MessageReceipt | None = (await db.execute(sqlalchemy.select(MessageReceipt).where(sqlalchemy.and_(MessageReceipt.message_id == selected_message.id, MessageReceipt.receiver_user_id != selected_user.id)))).scalars().first()
        return bool(message_receipt)