import fastapi
import redis
import asyncio
import contextlib
import sqlalchemy.orm

import websocket_connection_manager
from backend.storage import *
from models import *
import websocket_listeners_service
import backend.routers.dependencies


async def websocket_chats_post_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_post_listener(redis_client, db, chats_websocket_connection_manager)



async def websocket_chats_put_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_put_listener(redis_client, db, chats_websocket_connection_manager)



async def websocket_chats_delete_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chats_delete_listener(redis_client, db, chats_websocket_connection_manager)


async def websocket_chat_users_post_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chat_users_post_listener(redis_client, db, chats_websocket_connection_manager)


async def websocket_chat_users_put_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chat_users_put_listener(redis_client, db, chats_websocket_connection_manager)


async def websocket_chat_users_delete_listener(
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session,
    chats_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager):

    await backend.routers.chats.websocket_listeners_service.websocket_chat_users_delete_listener(redis_client, db, chats_websocket_connection_manager)

@contextlib.asynccontextmanager
async def on_startup(app):
    post_task = asyncio.create_task(websocket_chats_post_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    put_task = asyncio.create_task(websocket_chats_put_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    delete_task = asyncio.create_task(websocket_chats_delete_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))

    chat_user_post_task = asyncio.create_task(websocket_chat_users_post_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    chat_user_put_task = asyncio.create_task(websocket_chat_users_put_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))
    chat_user_delete_task = asyncio.create_task(websocket_chat_users_delete_listener(await redis_handler.get_redis_client(), await database.get_db(), await websocket_connection_manager.get_chats_websocket_connection_manager()))

    yield
    post_task.cancel()
    put_task.cancel()
    delete_task.cancel()
    chat_user_post_task.cancel()
    chat_user_put_task.cancel()
    chat_user_delete_task.cancel()


chats_websocket_listener_router = fastapi.APIRouter(lifespan = on_startup)