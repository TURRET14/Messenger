import fastapi
import sqlalchemy.orm
import redis

from backend.storage import *
import websocket_listeners_service
import websocket_connection_manager

messages_websocket_router = fastapi.APIRouter()

@messages_websocket_router.on_startup()
async def websocket_messages_post_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_post_subscriber(db, redis_client, messages_websocket_connection_manager)


@messages_websocket_router.on_startup()
async def websocket_messages_put_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_put_subscriber(db, redis_client, messages_websocket_connection_manager)


@messages_websocket_router.on_startup()
async def websocket_messages_delete_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessagesWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_messages_websocket_connection_manager)):

    await websocket_listeners_service.websocket_messages_delete_subscriber(db, redis_client, messages_websocket_connection_manager)