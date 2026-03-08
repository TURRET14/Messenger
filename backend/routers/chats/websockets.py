import fastapi
from fastapi import WebSocketException

import backend.routers.dependencies
import websocket_connection_manager
from backend.storage import *

chats_websockets = fastapi.APIRouter()

async def websocket_connection_body(
    websocket: fastapi.WebSocket,
    websockets_list: dict[User, set[fastapi.WebSocket]],
    selected_user: User):

    await websocket.accept()

    if not websockets_list[selected_user]:
        websockets_list[selected_user] = set()

    websockets_list[selected_user].add(websocket)

    try:
        while True:
            await websocket.receive()

    except WebSocketException:
        websockets_list[selected_user].remove(websocket)
        if len(websockets_list[selected_user]) == 0:
            websockets_list.pop(selected_user)
        await websocket.close()


@chats_websockets.websocket("/chats/post")
async def websocket_chats_post(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, messages_websocket_connection_manager.chats_post_websockets, selected_user)


@chats_websockets.websocket("/chats/put")
async def websocket_chats_put(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, messages_websocket_connection_manager.chats_put_websockets, selected_user)


@chats_websockets.websocket("/chats/delete")
async def websocket_chats_delete(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_connection_body(websocket, messages_websocket_connection_manager.chats_delete_websockets, selected_user)


async def websocket_chat_users_connection_body(
    websocket: fastapi.WebSocket,
    selected_chat: Chat,
    websockets_list: dict[User, dict[Chat, set[fastapi.WebSocket]]],
    selected_user: User):

    await websocket.accept()

    if not websockets_list[selected_user]:
        websockets_list[selected_user] = dict()

    if not websockets_list[selected_user][selected_chat]:
        websockets_list[selected_user][selected_chat] = set()


    websockets_list[selected_user][selected_chat].add(websocket)

    try:
        while True:
            await websocket.receive()

    except WebSocketException:
        websockets_list[selected_user][selected_chat].remove(websocket)
        if len(websockets_list[selected_user][selected_chat]) == 0:
            websockets_list[selected_user].pop(selected_chat)
        if len(websockets_list[selected_user]) == 0:
            websockets_list.pop(selected_user)
        await websocket.close()


@chats_websockets.websocket("/chats/{chat_id}/users/post")
async def websocket_chat_users_post(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_chat_users_connection_body(websocket, selected_chat, messages_websocket_connection_manager.chat_users_post_websockets, selected_user)


@chats_websockets.websocket("/chats/{chat_id}/users/put")
async def websocket_chat_users_put(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_chat_users_connection_body(websocket, selected_chat, messages_websocket_connection_manager.chat_users_put_websockets, selected_user)


@chats_websockets.websocket("/chats/{chat_id}/users/delete")
async def websocket_chat_users_delete(
    websocket: fastapi.WebSocket,
    messages_websocket_connection_manager: websocket_connection_manager.ChatsWebsocketConnectionManager = fastapi.Depends(websocket_connection_manager.get_chats_websocket_connection_manager),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)):

    await websocket_chat_users_connection_body(websocket, selected_chat, messages_websocket_connection_manager.chat_users_delete_websockets, selected_user)