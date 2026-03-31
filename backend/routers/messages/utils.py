from typing import Sequence

import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.routers.messages.models import ReadMarkData
from backend.storage import *

async def get_chat_user_membership(
    selected_chat_id: int,
    selected_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership:

    chat_membership: ChatMembership = ((await db.execute(
    sqlalchemy.select(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat_id, ChatMembership.chat_user_id == selected_user_id))))
                                       .scalars().first())

    return chat_membership


async def is_chat_user_owner(
    selected_chat_id: int,
    selected_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    selected_chat: Chat = ((await db.execute(
    sqlalchemy.select(Chat)
    .where(sqlalchemy.and_(Chat.id == selected_chat_id, Chat.owner_user_id == selected_user_id))))
    .scalars().first())

    return bool(selected_chat)

async def does_message_belong_to_chat(
    selected_chat_id: int,
    selected_message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    selected_message: Message = ((await db.execute(
    sqlalchemy.select(Message)
    .where(sqlalchemy.and_(Message.chat_id == selected_chat_id, Message.id == selected_message_id))))
    .scalars().first())

    return bool(selected_message)


async def is_message_read(
    selected_message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    message_receipt: MessageReceipt = (await db.execute(sqlalchemy.select(MessageReceipt).where(MessageReceipt.message_id == selected_message_id))).scalars().first()

    return bool(message_receipt)


async def do_messages_have_same_parent_message(
    first_message_id: int,
    second_message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    messages: Sequence[Message] = ((await db.execute(
    sqlalchemy.select(Message)
    .where(sqlalchemy.and_(Message.id.in_([first_message_id, second_message_id]),
    Message.parent_message_id == sqlalchemy.select(Message.parent_message_id).select_from(Message).where(Message.id == first_message_id)))))
    .scalars().all())

    return len(messages) >= 2


async def does_message_have_parent_message(
    selected_message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    selected_message: Message = (await db.execute(sqlalchemy.select(Message).where(sqlalchemy.and_(Message.id == selected_message_id, Message.parent_message_id != None)))).scalars().first()

    return bool(selected_message)


async def is_user_message_sender(
    user_id: int,
    message_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    selected_message: Message = (await db.execute(sqlalchemy.select(Message).where(sqlalchemy.and_(Message.id == message_id, Message.sender_user_id == user_id)))).scalars().first()

    return bool(selected_message)