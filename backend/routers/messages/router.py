import asyncio

import fastapi
import minio
import sqlalchemy.orm
import redis

from models import *
import implementation
import backend.dependencies
from backend.storage import *
from backend.routers.connection_manager import *

messages_router = fastapi.APIRouter()

@messages_router.get("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse)
async def get_chat_messages(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.messages.implementation.get_chat_messages(offset_multiplier, selected_chat, current_user, db)


@messages_router.post("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse)
async def post_message(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    data: MessageModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.messages.implementation.post_message(selected_chat, data, current_user, redis_client, db)


@messages_router.delete("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.JSONResponse)
async def delete_message(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.messages.implementation.delete_message(selected_chat, selected_message, current_user, redis_client, db)

@messages_router.put("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.JSONResponse)
async def update_message(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    data: MessageModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.messages.implementation.update_message(selected_chat, selected_message, data, current_user, redis_client, db)

@messages_router.on_startup()
async def websocket_messages_post_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    websocket_connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager)):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("messages_post")
    for selected_message_id in pubsub.listen():
        asyncio.run(websocket_connection_manager.messages_post(selected_message_id, db))


@messages_router.on_startup()
async def websocket_messages_put_subscriber(
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.Redis = fastapi.Depends(redis_handler.get_redis_client),
    websocket_connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager)):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("messages_put")
    for selected_message_id in pubsub.listen():
        asyncio.run(websocket_connection_manager.messages_put(selected_message_id, db))