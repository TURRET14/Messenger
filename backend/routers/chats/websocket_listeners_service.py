import redis.asyncio
import asyncio
import json
import sqlalchemy.orm

import websocket_connection_manager
from models import *


async def websocket_chats_post_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chats_post")
    async for selected_chat_with_receivers in pubsub.listen():
        chat_with_receivers: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(selected_chat_with_receivers)
        asyncio.create_task(chats_websocket_connection_manager.chats_post_update(chat_with_receivers, True, db))


async def websocket_chats_put_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chats_put")
    async for selected_chat_with_receivers in pubsub.listen():
        chat_with_receivers: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(json.loads(selected_chat_with_receivers))
        asyncio.create_task(chats_websocket_connection_manager.chats_post_update(chat_with_receivers, False, db))


async def websocket_chats_delete_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chats_delete")
    async for selected_chat_with_receivers in pubsub.listen():
        chat_with_receivers: ChatWithReceiversModel = ChatWithReceiversModel.model_validate(json.loads(selected_chat_with_receivers))
        asyncio.create_task(chats_websocket_connection_manager.chats_delete(chat_with_receivers, db))


async def websocket_chat_users_post_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chat_users_post")
    async for selected_chat_user_with_receivers in pubsub.listen():
        chat_user_with_receivers: ChatUserWithReceiversModel = ChatUserWithReceiversModel.model_validate(selected_chat_user_with_receivers)
        asyncio.create_task(chats_websocket_connection_manager.chat_users_post_update(chat_user_with_receivers, True, db))


async def websocket_chat_users_put_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chat_users_put")
    async for selected_chat_user_with_receivers in pubsub.listen():
        chat_user_with_receivers: ChatUserWithReceiversModel = ChatUserWithReceiversModel.model_validate(selected_chat_user_with_receivers)
        asyncio.create_task(chats_websocket_connection_manager.chat_users_post_update(chat_user_with_receivers, False, db))


async def websocket_chat_users_delete_listener(
    redis_client: redis.asyncio.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chat_users_delete")
    async for selected_chat_user_with_receivers in pubsub.listen():
        chat_user_with_receivers: ChatUserWithReceiversModel = ChatUserWithReceiversModel.model_validate(selected_chat_user_with_receivers)
        asyncio.create_task(chats_websocket_connection_manager.chat_users_delete(chat_user_with_receivers, db))