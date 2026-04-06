import fastapi
from fastapi import WebSocketException

import backend.routers.dependencies
from backend.routers.chats.websockets.connection_manager import (get_websocket_connection_manager, WebsocketConnectionManager, WebsocketType)
from backend.storage import *
from backend.routers.common_validators import validators

chats_websockets = fastapi.APIRouter()

async def websocket_connection_body(
    websocket: fastapi.WebSocket,
    websocket_type: WebsocketType,
    selected_user_id: int,
    connection_manager: WebsocketConnectionManager):

    await connection_manager.add_websocket(websocket, selected_user_id, websocket_type)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketException:
        await connection_manager.remove_websocket(websocket, selected_user_id, websocket_type)


async def memberships_websocket_connection_body(
    websocket: fastapi.WebSocket,
    websocket_type: WebsocketType,
    selected_chat: Chat,
    selected_user: User,
    connection_manager: WebsocketConnectionManager):

    async with async_session_maker() as db:
        await validators.validate_chat_user_membership(selected_chat, selected_user, db)

    await connection_manager.add_websocket(websocket, selected_user.id, websocket_type, selected_chat.id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketException:
        await connection_manager.remove_websocket(websocket, selected_user.id, websocket_type, selected_chat.id)


@chats_websockets.websocket("/chats/post")
async def websocket_chats_post(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, WebsocketType.CHAT_POST, selected_user.id, websocket_connection_manager)


@chats_websockets.websocket("/chats/put")
async def websocket_chats_put(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, WebsocketType.CHAT_PUT, selected_user.id, websocket_connection_manager)


@chats_websockets.websocket("/chats/delete")
async def websocket_chats_delete(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, WebsocketType.CHAT_DELETE, selected_user.id, websocket_connection_manager)


@chats_websockets.websocket("/chats/{chat_id}/memberships/post")
async def websocket_chat_memberships_post(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await memberships_websocket_connection_body(websocket, WebsocketType.CHAT_MEMBERSHIP_POST, selected_chat, selected_user, connection_manager)


@chats_websockets.websocket("/chats/{chat_id}/memberships/put")
async def websocket_chat_memberships_put(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await memberships_websocket_connection_body(websocket, WebsocketType.CHAT_MEMBERSHIP_PUT, selected_chat, selected_user, connection_manager)


@chats_websockets.websocket("/chats/{chat_id}/memberships/delete")
async def websocket_chat_memberships_delete(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await memberships_websocket_connection_body(websocket, WebsocketType.CHAT_MEMBERSHIP_DELETE, selected_chat, selected_user, connection_manager)


@chats_websockets.websocket("/chats/messages/last")
async def websocket_chat_last_message_update(
    websocket: fastapi.WebSocket,
    connection_manager: WebsocketConnectionManager = fastapi.Depends(get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, WebsocketType.CHAT_LAST_MESSAGE_UPDATE, selected_user.id, connection_manager)