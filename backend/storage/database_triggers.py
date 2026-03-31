import asyncio

import redis.asyncio
import sqlalchemy.event
import sqlalchemy.orm
import sqlalchemy.dialects

from backend.routers.message_attachments.models import MessageAttachmentModel, MessageAttachmentModelWithReceivers
from backend.routers.messages.models import MessageIDWithChatIDWithReceiversModel, ReadMarkData
from database import *
import redis_handler
from backend.routers.chats.models import *

async def chat_user_after_insert(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: ChatMembership):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("chats_post", ChatWithReceiversModel(
    chat_id = target.chat_id, receivers = [target.chat_user_id], is_avatar_changed = True).model_dump_json()))

    asyncio.create_task(redis_client.publish("chat_users_post", ChatUserWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id,
    receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))

async def chat_user_after_delete(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: ChatMembership):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("chats_delete", ChatWithReceiversModel(
    chat_id = target.chat_id, receivers = [target.chat_user_id], is_avatar_changed = False).model_dump_json()))

    asyncio.create_task(redis_client.publish("chat_users_delete", ChatUserWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id,
    receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))


async def chat_user_after_update(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: ChatMembership):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("chat_users_put", ChatUserWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id,
    receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))

async def chat_after_update(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: Chat):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("chats_put", ChatWithReceiversModel(
    chat_id = target.id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.id)).scalars().all()),
    is_avatar_changed = sqlalchemy.inspect(target).attrs.avatar_photo_path.history.has_changes()).model_dump_json()))


async def message_after_insert(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: Message):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("messages_post", MessageIDWithChatIDWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))


async def message_after_update(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: Message):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("messages_put", MessageIDWithChatIDWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))


async def message_after_delete(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: Message):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    asyncio.create_task(redis_client.publish("messages_delete", MessageIDWithChatIDWithReceiversModel(
    id = target.id,
    chat_id = target.chat_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == target.chat_id)).scalars().all())).model_dump_json()))


async def message_read_mark_after_insert(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: MessageReceipt):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    chat_id: int = db.execute(sqlalchemy.select(Message.chat_id).select_from(Message).where(Message.id == target.message_id)).scalar()

    asyncio.create_task(redis_client.publish("message_read_marks_post", ReadMarkData(
    id = target.id,
    chat_id = chat_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == chat_id)).scalars().all()), message_id = target.message_id, reader_id = target.receiver_user_id).model_dump_json()))


async def message_attachment_after_insert(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: MessageAttachment):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    chat_id: int = db.execute(sqlalchemy.select(Message.chat_id).select_from(Message).where(Message.id == target.message_id)).scalar()

    asyncio.create_task(redis_client.publish("message_attachments_post", MessageAttachmentModelWithReceivers(
    id = target.id,
    chat_id = chat_id, message_id = target.message_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == chat_id)).scalars().all())).model_dump_json()))


async def message_attachment_after_delete(mapper: sqlalchemy.orm.Mapper, connection: sqlalchemy.engine.Connection, target: MessageAttachment):
    db: sqlalchemy.orm.session.Session = await get_db()
    redis_client: redis.asyncio.Redis = await redis_handler.get_redis_client()

    chat_id: int = db.execute(sqlalchemy.select(Message.chat_id).select_from(Message).where(Message.id == target.message_id)).scalar()

    asyncio.create_task(redis_client.publish("message_attachments_delete", MessageAttachmentModelWithReceivers(
    id = target.id,
    chat_id = chat_id, message_id = target.message_id, receivers = list(db.execute(sqlalchemy.select(ChatMembership.chat_user_id).select_from(ChatMembership).where(ChatMembership.chat_id == chat_id)).scalars().all())).model_dump_json()))