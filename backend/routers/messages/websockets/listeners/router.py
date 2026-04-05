import fastapi
import asyncio
import contextlib

from backend.storage import *
from backend.routers.messages.websockets.listeners import service
from backend.routers.messages.websockets.connection_manager import (get_websocket_connection_manager, WebsocketConnectionManager)


async def websocket_messages_post_listener(
    redis_client: RedisClient,
    messages_websocket_connection_manager: WebsocketConnectionManager):

    await service.websocket_messages_post_listener(redis_client, messages_websocket_connection_manager)



async def websocket_messages_put_listener(
    redis_client: RedisClient,
    messages_websocket_connection_manager: WebsocketConnectionManager):

    await service.websocket_messages_put_listener(redis_client, messages_websocket_connection_manager)



async def websocket_messages_delete_listener(
    redis_client: RedisClient,
    messages_websocket_connection_manager: WebsocketConnectionManager):

    await service.websocket_messages_delete_listener(redis_client, messages_websocket_connection_manager)


async def websocket_messages_read_mark_post_listener(
    redis_client: RedisClient,
    messages_websocket_connection_manager: WebsocketConnectionManager):

    await service.websocket_messages_read_mark_post_listener(redis_client, messages_websocket_connection_manager)


@contextlib.asynccontextmanager
async def on_startup(app):
    redis_client: RedisClient = await redis_handler.get_redis_client()
    connection_manager: WebsocketConnectionManager = await get_websocket_connection_manager()

    post_task = asyncio.create_task(websocket_messages_post_listener(redis_client, connection_manager))
    put_task = asyncio.create_task(websocket_messages_put_listener(redis_client, connection_manager))
    delete_task = asyncio.create_task(websocket_messages_delete_listener(redis_client, connection_manager))
    post_read_mark_task = asyncio.create_task(websocket_messages_read_mark_post_listener(redis_client, connection_manager))

    yield

    post_task.cancel()
    put_task.cancel()
    delete_task.cancel()
    post_read_mark_task.cancel()


messages_websocket_listener_router = fastapi.APIRouter(lifespan = on_startup)