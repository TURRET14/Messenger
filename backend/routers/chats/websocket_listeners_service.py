import redis
import asyncio
import json

import websocket_connection_manager
from models import *


async def websocket_chats_post_subscriber(
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("chats_post")
    for selected_chat_with_receivers in pubsub.listen():
        data: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(json.loads(selected_chat_with_receivers))
        asyncio.run(messages_websocket_connection_manager.chats_post_update(data, True))


async def websocket_chats_put_subscriber(
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("chats_put")
    for selected_chat_with_receivers in pubsub.listen():
        data: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(json.loads(selected_chat_with_receivers))
        asyncio.run(messages_websocket_connection_manager.chats_post_update(data, False))


async def websocket_chats_delete_subscriber(
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("chats_delete")
    for selected_chat_with_receivers in pubsub.listen():
        data: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(json.loads(selected_chat_with_receivers))
        asyncio.run(messages_websocket_connection_manager.chats_delete(data))