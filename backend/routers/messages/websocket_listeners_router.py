import fastapi
import sqlalchemy.orm
import redis
import asyncio
import contextlib

from backend.storage import *
import websocket_listeners_service
import websocket_connection_manager


async def websocket_messages_post_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_post_subscriber(db, redis_client, messages_websocket_connection_manager)



async def websocket_messages_put_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_put_subscriber(db, redis_client, messages_websocket_connection_manager)



async def websocket_messages_delete_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_delete_subscriber(db, redis_client, messages_websocket_connection_manager)


@contextlib.asynccontextmanager
async def on_startup(app: fastapi.FastAPI):
    post_task = asyncio.create_task(websocket_messages_post_subscriber(await get_db(), await redis_handler.get_redis_client(), await websocket_connection_manager.get_messages_websocket_connection_manager()))
    put_task = asyncio.create_task(websocket_messages_put_subscriber(await get_db(), await redis_handler.get_redis_client(), await websocket_connection_manager.get_messages_websocket_connection_manager()))
    delete_task = asyncio.create_task(websocket_messages_delete_subscriber(await get_db(), await redis_handler.get_redis_client(), await websocket_connection_manager.get_messages_websocket_connection_manager()))

    yield
    post_task.cancel()
    put_task.cancel()
    delete_task.cancel()


messages_websocket_router = fastapi.APIRouter(lifespan = on_startup)