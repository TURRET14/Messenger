import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence
import utils
import enum

from backend.routers.messages.websockets.models import (MessagePubsubWebsocketModel, ReadMarkPubsubWebsocketModel)
from backend.routers.common_models import (IDModel)
from backend.routers.messages.response_models import (MessageResponseModel, MessageReadMarkResponseModel)

class WebsocketType(enum.Enum):
    MESSAGE_POST = "MESSAGE_POST"
    MESSAGE_PUT = "MESSAGE_DELETE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    MESSAGE_READ_POST = "MESSAGE_READ_POST"

class WebsocketConnectionManager:
    # dict [User.id, dict[Chat.id, set[fastapi.WebSocket]]]
    messages_post_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    messages_put_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    messages_delete_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    message_read_post_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

    async def messages_post_update(
        self,
        message_data: MessagePubsubWebsocketModel,
        is_post: bool,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(message_data.chat_id, db)

        websockets_container: dict[int, dict[int, set[fastapi.WebSocket]]]
        if is_post:
            websockets_container = self.messages_post_websockets
        else:
            websockets_container = self.messages_put_websockets

        for receiver_id in message_receivers_list:
            for websocket in websockets_container.get(receiver_id, dict()).get(message_data.chat_id, set()):
                message_response_data: MessageResponseModel = MessageResponseModel(
                id = message_data.id,
                chat_id = message_data.chat_id,
                date_and_time_sent = message_data.date_and_time_sent,
                date_and_time_edited = message_data.date_and_time_edited,
                message_text = message_data.message_text,
                is_read = message_data.is_read)
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_response_data))


    async def messages_delete(
        self,
        message_data: MessagePubsubWebsocketModel,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(message_data.chat_id, db)

        for receiver_id in message_receivers_list:
            for websocket in self.messages_delete_websockets.get(receiver_id, dict()).get(message_data.chat_id, set()):
                message_response_data: IDModel = IDModel(id = message_data.id)
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_response_data))


    async def message_read_mark_post(
        self,
        message_read_mark_data: ReadMarkPubsubWebsocketModel,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(message_read_mark_data.chat_id, db)

        for receiver_id in message_receivers_list:
            for websocket in self.message_read_post_websockets.get(receiver_id, dict()).get(message_read_mark_data.chat_id, set()):
                message_read_mark_response: MessageReadMarkResponseModel = MessageReadMarkResponseModel(
                id = message_read_mark_data.id,
                chat_id = message_read_mark_data.chat_id,
                message_id = message_read_mark_data.message_id,
                reader_user_id = message_read_mark_data.reader_user_id)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_read_mark_response))


    async def get_websocket_dict(self, websocket_type: WebsocketType) -> dict[int, dict[int, set[fastapi.WebSocket]]]:
        websockets_dict: dict[int, dict[int, set[fastapi.WebSocket]]]

        match websocket_type:
            case WebsocketType.MESSAGE_POST:
                websockets_dict = self.messages_post_websockets
            case WebsocketType.MESSAGE_PUT:
                websockets_dict = self.messages_put_websockets
            case WebsocketType.MESSAGE_DELETE:
                websockets_dict = self.messages_delete_websockets
            case WebsocketType.MESSAGE_READ_POST:
                websockets_dict = self.message_read_post_websockets

        return websockets_dict


    async def add_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_chat_id: int,
        selected_user_id: int,
        websocket_type: WebsocketType):

        websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = await self.get_websocket_dict(websocket_type)

        await websocket.accept()

        if not websockets_list.get(selected_user_id, None):
            websockets_list[selected_user_id] = dict()

        if not websockets_list.get(selected_user_id, dict()).get(selected_chat_id, set()):
            websockets_list[selected_user_id][selected_chat_id] = set()


        websockets_list[selected_user_id][selected_chat_id].add(websocket)


    async def remove_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_chat_id: int,
        selected_user_id: int,
        websocket_type: WebsocketType):

        websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = await self.get_websocket_dict(websocket_type)

        if selected_user_id not in websockets_list:
            return
        elif selected_chat_id not in websockets_list[selected_user_id]:
            return

        websockets_list.get(selected_user_id, dict()).get(selected_chat_id, set()).discard(websocket)

        if len(websockets_list[selected_user_id][selected_chat_id]) == 0:
            websockets_list[selected_user_id].pop(selected_chat_id)
        if len(websockets_list[selected_user_id]) == 0:
            websockets_list.pop(selected_user_id)

        await websocket.close()


websocket_connection_manager_instance: WebsocketConnectionManager = WebsocketConnectionManager()

async def get_websocket_connection_manager():
    return websocket_connection_manager_instance