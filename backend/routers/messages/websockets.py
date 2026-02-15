import fastapi
import sqlalchemy
from fastapi import WebSocketException

import backend.dependencies
import backend.routers.connection_manager
from backend.storage import *

messages_websockets = fastapi.APIRouter()

@messages_websockets.websocket("/messages/post")
async def websocket_messages_post(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: backend.routers.connection_manager.WebsocketConnectionManager = fastapi.Depends(backend.routers.connection_manager.get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user)):

    await websocket.accept()

    if not websocket_connection_manager.messages_post_websockets[selected_user]:
        websocket_connection_manager.messages_post_websockets[selected_user] = set()

    websocket_connection_manager.messages_post_websockets[selected_user].add(websocket)

    try:
        while True:
            await websocket.receive()

    except WebSocketException:
        websocket_connection_manager.messages_post_websockets[selected_user].remove(websocket)
        if len(websocket_connection_manager.messages_post_websockets[selected_user]) == 0:
            websocket_connection_manager.messages_post_websockets.pop(selected_user)
        await websocket.close()


@messages_websockets.websocket("/messages/put")
async def websocket_messages_put(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: backend.routers.connection_manager.WebsocketConnectionManager = fastapi.Depends(backend.routers.connection_manager.get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user)):

    await websocket.accept()

    if not websocket_connection_manager.messages_put_websockets[selected_user]:
        websocket_connection_manager.messages_put_websockets[selected_user] = set()

    websocket_connection_manager.messages_put_websockets[selected_user].add(websocket)

    try:
        while True:
            await websocket.receive()

    except WebSocketException:
        websocket_connection_manager.messages_put_websockets[selected_user].remove(websocket)
        if len(websocket_connection_manager.messages_put_websockets[selected_user]) == 0:
            websocket_connection_manager.messages_put_websockets.pop(selected_user)
        await websocket.close()


@messages_websockets.websocket("/messages/delete")
async def websocket_messages_delete(
    websocket: fastapi.WebSocket,
    websocket_connection_manager: backend.routers.connection_manager.WebsocketConnectionManager = fastapi.Depends(backend.routers.connection_manager.get_websocket_connection_manager),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user)):

    await websocket.accept()

    if not websocket_connection_manager.messages_delete_websockets[selected_user]:
        websocket_connection_manager.messages_delete_websockets[selected_user] = set()

    websocket_connection_manager.messages_delete_websockets[selected_user].add(websocket)

    try:
        while True:
            await websocket.receive()

    except WebSocketException:
        websocket_connection_manager.messages_delete_websockets[selected_user].remove(websocket)
        if len(websocket_connection_manager.messages_delete_websockets[selected_user]) == 0:
            websocket_connection_manager.messages_delete_websockets.pop(selected_user)
        await websocket.close()