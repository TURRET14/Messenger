import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *

async def is_message_read(
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool | None:

    if selected_message.sender_user_id == selected_user.id:
        message_receipt: MessageReceipt | None = ((await db.execute(
        sqlalchemy.select(MessageReceipt)
        .where(sqlalchemy.and_(MessageReceipt.message_id == selected_message.id,
        MessageReceipt.receiver_user_id != selected_user.id))))
        .scalars().first())

        return bool(message_receipt)
    else:
        return None




async def is_message_last_chat_message(
    selected_chat: Chat,
    selected_message: Message,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    return bool((await db.execute(
    sqlalchemy.select(Message.id)
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id == selected_message.parent_message_id)
    .order_by(Message.date_and_time_sent.desc()))))
    .scalars().first() == selected_message.id)


async def get_chat_last_root_message(
    selected_chat: Chat,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Message | None:

    last_chat_root_message: Message | None = ((await db.execute(sqlalchemy.select(Message)
    .select_from(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat.id, Message.parent_message_id is None))
    .order_by(Message.date_and_time_sent.desc())
    .limit(1)))
    .scalars().first())

    return last_chat_root_message


async def does_message_have_attachments(
    selected_message: Message,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    return bool((await db.execute(
    sqlalchemy.select(1).
    select_from(MessageAttachment)
    .where(MessageAttachment.message_id == selected_message.id)
    .limit(1)))
    .scalars().first())