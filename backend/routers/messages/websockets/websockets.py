import fastapi
import starlette.websockets

import backend.environment as environment
import backend.routers.dependencies
from backend.routers.messages.websockets.connection_manager import (get_websocket_connection_manager, WebsocketConnectionManager, WebsocketType)
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
from backend.routers.common_validators import validators

messages_websockets_router = fastapi.APIRouter()

async def websocket_connection_body(
    websocket: fastapi.WebSocket,
    websocket_type: WebsocketType,
    connection_manager: WebsocketConnectionManager,
    chat_id: int,
    session_id: str | None,
    parent_message_id: int | None = None):

    redis_client: RedisClient = RedisClient(
        host = environment.REDIS_HOST,
        port = int(environment.REDIS_PORT),
        password = environment.REDIS_PASSWORD,
        db = int(environment.REDIS_DB))

    try:
        async with async_session_maker() as db:
            selected_chat: Chat = await backend.routers.dependencies.get_chat_by_path_id(chat_id, db)
            selected_user: User = await backend.routers.dependencies.get_session_user(session_id, db, redis_client)
            parent_message: Message | None = await backend.routers.dependencies.get_parent_message_by_query_id(parent_message_id, db)

            await validators.validate_chat_user_membership(selected_chat, selected_user, db)
    finally:
        await redis_client.client.aclose()

    if parent_message and parent_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_belong_to_chat_error.error_status_code, detail = ErrorRegistry.message_does_not_belong_to_chat_error)

    parent_message_id: int | None = parent_message.id if parent_message else None

    await connection_manager.add_websocket(websocket, selected_chat.id, selected_user.id, websocket_type, parent_message_id)

    try:
        while True:
            await websocket.receive_text()
    except starlette.websockets.WebSocketDisconnect:
        await connection_manager.remove_websocket(websocket, selected_chat.id, selected_user.id, websocket_type, parent_message_id)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/post")
async def websocket_messages_post(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    chat_id: int = fastapi.Path(ge = 0),
    parent_message_id: int | None = fastapi.Query(ge = 0, default = None),
    session_id: str | None = fastapi.Cookie(default = None)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_POST, connection_manager, chat_id, session_id, parent_message_id)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/put")
async def websocket_messages_put(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    chat_id: int = fastapi.Path(ge = 0),
    parent_message_id: int | None = fastapi.Query(ge = 0, default = None),
    session_id: str | None = fastapi.Cookie(default = None)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_PUT, connection_manager, chat_id, session_id, parent_message_id)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/delete")
async def websocket_messages_delete(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    chat_id: int = fastapi.Path(ge = 0),
    parent_message_id: int | None = fastapi.Query(ge = 0, default = None),
    session_id: str | None = fastapi.Cookie(default = None)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_DELETE, connection_manager, chat_id, session_id, parent_message_id)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/read")
async def websocket_messages_read(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    chat_id: int = fastapi.Path(ge = 0),
    session_id: str | None = fastapi.Cookie(default = None)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_READ_POST, connection_manager, chat_id, session_id)
