import fastapi
import minio
import redis
import sqlalchemy.orm

import websocket_connection_manager
from backend.storage import *
from models import *
import websocket_listeners_service
import backend.routers.dependencies

chats_websocket_listener_router = fastapi.APIRouter()

@chats_websocket_listener_router.on_startup()
async def websocket_messages_post_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_post_subscriber(redis_client, messages_websocket_connection_manager)


@chats_websocket_listener_router.on_startup()
async def websocket_messages_put_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_put_subscriber(redis_client, messages_websocket_connection_manager)


@chats_websocket_listener_router.on_startup()
async def websocket_messages_delete_subscriber(
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_delete_subscriber(redis_client, messages_websocket_connection_manager)
