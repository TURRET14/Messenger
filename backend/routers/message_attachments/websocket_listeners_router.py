import fastapi
import sqlalchemy.orm
import redis

from backend.storage import *
import websocket_listeners_service
import websocket_connection_manager

message_websocket_attachments_router = fastapi.APIRouter()

@message_websocket_attachments_router.on_startup()
async def websocket_message_attachments_post_listener(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager)):

    await websocket_listeners_service.websocket_message_attachments_post_subscriber(db, redis_client, messages_websocket_connection_manager)

@message_websocket_attachments_router.on_startup()
async def websocket_message_attachments_delete_listener(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager)):

    await websocket_listeners_service.websocket_message_attachments_delete_subscriber(db, redis_client, messages_websocket_connection_manager)