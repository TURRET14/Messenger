import redis
import sqlalchemy.orm
import json
import asyncio

from models import *
import websocket_connection_manager


async def websocket_messages_post_subscriber(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("messages_post")
    for selected_message_id in pubsub.listen():
        asyncio.create_task(messages_websocket_connection_manager.messages_post_update(selected_message_id, True, db))


async def websocket_messages_put_subscriber(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("messages_put")
    for selected_message_id in pubsub.listen():
        asyncio.create_task(messages_websocket_connection_manager.messages_post_update(selected_message_id, False, db))


async def websocket_messages_delete_subscriber(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("messages_delete")
    for selected_message_id_and_chat_id in pubsub.listen():
        message_data: MessageDeleteModel = MessageDeleteModel.model_validate(json.loads(selected_message_id_and_chat_id))
        asyncio.create_task(messages_websocket_connection_manager.messages_delete(message_data, db))