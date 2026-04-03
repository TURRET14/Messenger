import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *

async def is_message_read(
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if selected_message.sender_user_id == selected_user.id:
        return True
    else:
        message_receipt: MessageReceipt | None = ((await db.execute(
        sqlalchemy.select(MessageReceipt)
        .where(sqlalchemy.and_(MessageReceipt.message_id == selected_message.id,
        MessageReceipt.receiver_user_id != selected_user.id))))
        .scalars().first())
        return bool(message_receipt)