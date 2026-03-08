import redis.asyncio
import sqlalchemy.orm
import json
import asyncio

from backend.routers.chats.models import ChatUserWithReceiversModel
from backend.routers.common_models import IDModel
from models import *
import websocket_connection_manager


async def websocket_messages_post_listener(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.asyncio.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("messages_post")
    async for selected_message_data in pubsub.listen():
        selected_message_data_model: MessageIDWithChatIDWithReceiversModel = MessageIDWithChatIDWithReceiversModel.model_validate(selected_message_data)
        asyncio.create_task(messages_websocket_connection_manager.messages_post_update(selected_message_data_model, True, db))


async def websocket_messages_put_listener(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.asyncio.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("messages_put")
    async for selected_message_data in pubsub.listen():
        selected_message_data_model: MessageIDWithChatIDWithReceiversModel = MessageIDWithChatIDWithReceiversModel.model_validate(selected_message_data)
        asyncio.create_task(messages_websocket_connection_manager.messages_post_update(selected_message_data_model, False, db))


async def websocket_messages_delete_listener(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.asyncio.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("messages_delete")
    async for selected_message_data in pubsub.listen():
        selected_message_data_model: MessageIDWithChatIDWithReceiversModel = MessageIDWithChatIDWithReceiversModel.model_validate(json.loads(selected_message_data))
        asyncio.create_task(messages_websocket_connection_manager.messages_delete(selected_message_data_model, db))


async def websocket_messages_read_mark_post_listener(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.asyncio.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("message_read_marks_post")
    async for selected_message_read_mark_data in pubsub.listen():
        selected_message_read_mark_data_model: ReadMarkData = ReadMarkData.model_validate(selected_message_read_mark_data)
        asyncio.create_task(messages_websocket_connection_manager.message_read_mark_post(selected_message_read_mark_data_model, db))
