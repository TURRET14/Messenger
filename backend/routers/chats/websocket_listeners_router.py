import fastapi
import minio
import redis
import sqlalchemy.orm
import asyncio
import contextlib

import websocket_connection_manager
from backend.storage import *
from models import *
import websocket_listeners_service
import backend.routers.dependencies


async def websocket_messages_post_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_post_subscriber(redis_client, messages_websocket_connection_manager)



async def websocket_messages_put_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_put_subscriber(redis_client, messages_websocket_connection_manager)



async def websocket_messages_delete_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_delete_subscriber(redis_client, messages_websocket_connection_manager)

@contextlib.asynccontextmanager
async def on_startup(app: fastapi.FastAPI):
    post_task = asyncio.create_task(websocket_messages_post_subscriber(await redis_handler.get_redis_client(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    put_task = asyncio.create_task(websocket_messages_put_subscriber(await redis_handler.get_redis_client(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    delete_task = asyncio.create_task(websocket_messages_delete_subscriber(await redis_handler.get_redis_client(), await websocket_connection_manager.get_chats_websocket_connection_manager()))

    yield
    post_task.cancel()
    put_task.cancel()
    delete_task.cancel()


chats_websocket_listener_router = fastapi.APIRouter(lifespan = on_startup)