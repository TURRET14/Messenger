import fastapi
from fastapi import WebSocketException

import backend.routers.dependencies
from backend.routers.messages.websockets.connection_manager import (get_websocket_connection_manager, WebsocketConnectionManager, WebsocketType)
from backend.storage import *
from backend.routers.errors import (ErrorRegistry)
from backend.routers.common_validators import validators

messages_websockets_router = fastapi.APIRouter()

async def websocket_connection_body(
    websocket: fastapi.WebSocket,
    websocket_type: WebsocketType,
    selected_chat: Chat,
    selected_user: User,
    connection_manager: WebsocketConnectionManager,
    parent_message: Message | None = None):

    async with async_session_maker() as db:
        await validators.validate_chat_user_membership(selected_chat, selected_user, db)

    if parent_message and parent_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.message_does_not_belong_to_chat_error.error_status_code, detail = ErrorRegistry.message_does_not_belong_to_chat_error)

    parent_message_id: int | None = parent_message.parent_message_id if parent_message else None

    await connection_manager.add_websocket(websocket, selected_chat.id, selected_user.id, websocket_type, parent_message_id)

    try:
        while True:
            await websocket.receive()
    except WebSocketException:
        await connection_manager.remove_websocket(websocket, selected_chat.id, selected_user.id, websocket_type, parent_message_id)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/post")
async def websocket_messages_post(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    parent_message: Message | None = fastapi.Depends(backend.routers.dependencies.get_parent_message_by_query_id)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_POST, selected_chat, selected_user, connection_manager, parent_message)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/put")
async def websocket_messages_put(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    parent_message: Message | None = fastapi.Depends(backend.routers.dependencies.get_parent_message_by_query_id)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_PUT, selected_chat, selected_user, connection_manager, parent_message)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/delete")
async def websocket_messages_delete(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    parent_message: Message | None = fastapi.Depends(backend.routers.dependencies.get_parent_message_by_query_id)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_DELETE, selected_chat, selected_user, connection_manager, parent_message)


@messages_websockets_router.websocket("/chats/{chat_id}/messages/read")
async def websocket_messages_read(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, WebsocketType.MESSAGE_READ_POST, selected_chat, selected_user, connection_manager)