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