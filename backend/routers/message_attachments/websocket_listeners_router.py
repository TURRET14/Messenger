import fastapi
import sqlalchemy.orm
import redis
import asyncio
import contextlib

from backend.storage import *
import websocket_listeners_service
import websocket_connection_manager


async def websocket_message_attachments_post_listener(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager)):

    await websocket_listeners_service.websocket_message_attachments_post_subscriber(db, redis_client, messages_websocket_connection_manager)


async def websocket_message_attachments_delete_listener(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager)):

    await websocket_listeners_service.websocket_message_attachments_delete_subscriber(db, redis_client, messages_websocket_connection_manager)


@contextlib.asynccontextmanager
async def on_startup(app):
    post_task = asyncio.create_task(websocket_message_attachments_post_listener(await get_db(), await redis_handler.get_redis_client(), await websocket_connection_manager.get_websocket_connection_manager()))
    delete_task = asyncio.create_task(websocket_message_attachments_delete_listener(await get_db(), await websocket_connection_manager.get_websocket_connection_manager()))

    yield
    post_task.cancel()
    delete_task.cancel()


message_websocket_attachments_router = fastapi.APIRouter(lifespan = on_startup)