import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence
import enum

from backend.routers.messages.websockets import utils
from backend.routers.messages.websockets.models import (MessagePubsubWebsocketModel, ReadMarkPubsubWebsocketModel)
from backend.routers.common_models import (IDModel)
from backend.routers.messages.response_models import (MessageResponseModel, MessageReadMarkResponseModel)
from backend.storage import *

class WebsocketType(enum.Enum):
    MESSAGE_POST = "MESSAGE_POST"
    MESSAGE_PUT = "MESSAGE_DELETE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    MESSAGE_READ_POST = "MESSAGE_READ_POST"

class WebsocketConnectionManager:
    # dict[User.id, dict[Chat.id, dict[Message.parent_message_id | None, set[fastapi.WebSocket]]]]
    messages_post_websockets: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = {}
    messages_put_websockets: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = {}
    messages_delete_websockets: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = {}

    # dict [User.id, dict[Chat.id, set[fastapi.WebSocket]]]
    message_read_post_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

    async def messages_post_update(
        self,
        message_data: MessagePubsubWebsocketModel,
        is_post: bool,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: list[int] = []

        selected_chat: Chat | None = ((await db.execute(
        sqlalchemy.select(Chat)
        .where(Chat.id == message_data.chat_id)))
        .scalars().first())

        if selected_chat and selected_chat.chat_kind == ChatKind.PROFILE:
            for user_id, chats_dict in self.messages_post_websockets.items():
                if chats_dict.get(message_data.chat_id, dict()).get(message_data.parent_message_id, set()):
                    message_receivers_list.append(user_id)
        else:
            message_receivers_list: list[int] = message_data.receivers

        websockets_container: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]]
        if is_post:
            websockets_container = self.messages_post_websockets
        else:
            websockets_container = self.messages_put_websockets

        for receiver_id in message_receivers_list:
            for websocket in websockets_container.get(receiver_id, dict()).get(message_data.chat_id, dict()).get(message_data.parent_message_id, set()):
                message_response_data: MessageResponseModel = MessageResponseModel(
                id = message_data.id,
                chat_id = message_data.chat_id,
                sender_user_id = message_data.sender_user_id,
                date_and_time_sent = message_data.date_and_time_sent,
                date_and_time_edited = message_data.date_and_time_edited,
                message_text = message_data.message_text,
                reply_message_id = message_data.reply_message_id,
                parent_message_id = message_data.parent_message_id,
                is_read = message_data.is_read)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_response_data))


    async def messages_delete(
        self,
        message_data: MessagePubsubWebsocketModel,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: list[int] = []

        selected_chat: Chat | None = ((await db.execute(
        sqlalchemy.select(Chat)
        .where(Chat.id == message_data.chat_id)))
        .scalars().first())

        if selected_chat and selected_chat.chat_kind == ChatKind.PROFILE:
            for user_id, chats_dict in self.messages_post_websockets.items():
                if chats_dict.get(message_data.chat_id, dict()).get(message_data.parent_message_id, set()):
                    message_receivers_list.append(user_id)
        else:
            message_receivers_list: list[int] = message_data.receivers

        for receiver_id in message_receivers_list:
            for websocket in self.messages_delete_websockets.get(receiver_id, dict()).get(message_data.chat_id, dict()).get(message_data.parent_message_id, set()):
                message_response_data: MessageResponseModel = MessageResponseModel(
                id = message_data.id,
                chat_id = message_data.chat_id,
                sender_user_id = message_data.sender_user_id,
                date_and_time_sent = message_data.date_and_time_sent,
                date_and_time_edited = message_data.date_and_time_edited,
                message_text = message_data.message_text,
                reply_message_id = message_data.reply_message_id,
                parent_message_id = message_data.parent_message_id,
                is_read = message_data.is_read)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_response_data))


    async def message_read_mark_post(
        self,
        message_read_mark_data: ReadMarkPubsubWebsocketModel):

        message_receivers_list: list[int] = message_read_mark_data.receivers

        for receiver_id in message_receivers_list:
            for websocket in self.message_read_post_websockets.get(receiver_id, dict()).get(message_read_mark_data.chat_id, set()):
                message_read_mark_response: MessageReadMarkResponseModel = MessageReadMarkResponseModel(
                id = message_read_mark_data.id,
                chat_id = message_read_mark_data.chat_id,
                message_id = message_read_mark_data.message_id,
                date_and_time_received = message_read_mark_data.date_and_time_received,
                reader_user_id = message_read_mark_data.reader_user_id)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_read_mark_response))


    async def get_websocket_dict(self, websocket_type: WebsocketType) -> dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]]:
        websockets_dict: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = {}

        match websocket_type:
            case WebsocketType.MESSAGE_POST:
                websockets_dict = self.messages_post_websockets
            case WebsocketType.MESSAGE_PUT:
                websockets_dict = self.messages_put_websockets
            case WebsocketType.MESSAGE_DELETE:
                websockets_dict = self.messages_delete_websockets

        return websockets_dict


    async def add_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_chat_id: int,
        selected_user_id: int,
        websocket_type: WebsocketType,
        parent_message_id: int | None = None):

        await websocket.accept()

        websockets_list: dict

        if websocket_type.MESSAGE_READ_POST:
            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = self.message_read_post_websockets

            if not websockets_list.get(selected_user_id, None):
                websockets_list[selected_user_id] = dict()

            if not websockets_list.get(selected_user_id, dict()).get(selected_chat_id, set()):
                websockets_list[selected_user_id][selected_chat_id] = set()

            websockets_list[selected_user_id][selected_chat_id].add(websocket)
        else:
            websockets_list: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = await self.get_websocket_dict(websocket_type)

            if not websockets_list.get(selected_user_id, None):
                websockets_list[selected_user_id] = dict()

            if not websockets_list.get(selected_user_id, dict()).get(selected_chat_id, dict()):
                websockets_list[selected_user_id][selected_chat_id] = dict()

            if not websockets_list.get(selected_user_id, dict()).get(selected_chat_id, dict()).get(parent_message_id, set()):
                websockets_list[selected_user_id][selected_chat_id][parent_message_id] = set()

            websockets_list[selected_user_id][selected_chat_id][parent_message_id].add(websocket)


    async def remove_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_chat_id: int,
        selected_user_id: int,
        websocket_type: WebsocketType,
        parent_message_id: int | None = None):
        if websocket_type.MESSAGE_READ_POST:
            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = self.message_read_post_websockets

            if selected_user_id not in websockets_list:
                return
            elif selected_chat_id not in websockets_list[selected_user_id]:
                return

            websockets_list.get(selected_user_id, dict()).get(selected_chat_id, set()).discard(websocket)

            if len(websockets_list[selected_user_id][selected_chat_id]) == 0:
                websockets_list[selected_user_id].pop(selected_chat_id)
            if len(websockets_list[selected_user_id]) == 0:
                websockets_list.pop(selected_user_id)
        else:
            websockets_list: dict[int, dict[int, dict[int | None, set[fastapi.WebSocket]]]] = await self.get_websocket_dict(websocket_type)

            if selected_user_id not in websockets_list:
                return
            elif selected_chat_id not in websockets_list[selected_user_id]:
                return
            elif parent_message_id not in websockets_list[selected_user_id][selected_chat_id]:
                return

            websockets_list.get(selected_user_id, dict()).get(selected_chat_id, dict()).get(parent_message_id, set()).discard(websocket)
            if len(websockets_list[selected_user_id][selected_chat_id][parent_message_id]) == 0:
                websockets_list[selected_user_id][selected_chat_id].pop(parent_message_id)
            if len(websockets_list[selected_user_id][selected_chat_id]) == 0:
                websockets_list[selected_user_id].pop(selected_chat_id)
            if len(websockets_list[selected_user_id]) == 0:
                websockets_list.pop(selected_user_id)
        await websocket.close()


websocket_connection_manager_instance: WebsocketConnectionManager = WebsocketConnectionManager()

async def get_websocket_connection_manager():
    return websocket_connection_manager_instance