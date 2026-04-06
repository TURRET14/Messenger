import fastapi
import asyncio
import contextlib

from backend.storage import *
from backend.routers.chats.websockets.connection_manager import (get_websocket_connection_manager, WebsocketConnectionManager)
from backend.routers.chats.websockets.listeners import service
import backend.routers.dependencies


async def websocket_chats_post_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chats_post_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chats_put_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chats_put_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chats_delete_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chats_delete_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chat_memberships_post_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chat_memberships_post_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chat_memberships_put_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chat_memberships_put_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chat_memberships_delete_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chat_memberships_delete_listener(redis_client, chats_websocket_connection_manager)


async def websocket_chat_last_message_update_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    await backend.routers.chats.websockets.listeners.websocket_listeners_service.websocket_chat_last_message_update_listener(redis_client, chats_websocket_connection_manager)


@contextlib.asynccontextmanager
async def on_startup(app):
    redis_client: RedisClient = await redis_handler.get_redis_client()
    connection_manager: WebsocketConnectionManager = await get_websocket_connection_manager()

    post_task = asyncio.create_task(websocket_chats_post_listener(redis_client, connection_manager))
    put_task = asyncio.create_task(websocket_chats_put_listener(redis_client, connection_manager))
    delete_task = asyncio.create_task(websocket_chats_delete_listener(redis_client, connection_manager))

    chat_user_post_task = asyncio.create_task(websocket_chat_memberships_post_listener(redis_client, connection_manager))
    chat_user_put_task = asyncio.create_task(websocket_chat_memberships_put_listener(redis_client, connection_manager))
    chat_user_delete_task = asyncio.create_task(websocket_chat_memberships_delete_listener(redis_client, connection_manager))

    chat_last_message_update_task = asyncio.create_task(websocket_chat_last_message_update_listener(redis_client, connection_manager))

    yield

    post_task.cancel()
    put_task.cancel()
    delete_task.cancel()
    chat_user_post_task.cancel()
    chat_user_put_task.cancel()
    chat_user_delete_task.cancel()
    chat_last_message_update_task.cancel()


chats_websocket_listener_router = fastapi.APIRouter(lifespan = on_startup)