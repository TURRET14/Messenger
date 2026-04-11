import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
import enum
from typing import Sequence

import backend
import backend.routers.messages.utils as messages_utils
from backend.routers.chats.response_models import ChatResponseModel, ChatMembershipResponseModel
from backend.routers.chats.websockets.models import (ChatMembershipPubsubModel, ChatPubsubModel)
from backend.routers.messages.response_models import (MessageResponseModel, LastMessageResponseModel)
from backend.routers.messages.websockets.models import (LastMessagePubsubWebsocketModel)
from backend.storage import *


class WebsocketType(enum.Enum):
    CHAT_POST = "CHAT_POST"
    CHAT_PUT = "CHAT_PUT"
    CHAT_DELETE = "CHAT_DELETE"
    
    CHAT_MEMBERSHIP_POST = "CHAT_MEMBERSHIP_POST"
    CHAT_MEMBERSHIP_PUT = "CHAT_MEMBERSHIP_PUT"
    CHAT_MEMBERSHIP_DELETE = "CHAT_MEMBERSHIP_DELETE"

    CHAT_LAST_MESSAGE_UPDATE = "CHAT_LAST_MESSAGE_UPDATE"


class WebsocketConnectionManager:
    # dict[User.id, set[fastapi.WebSocket]]
    chats_post_websockets: dict[int, set[fastapi.WebSocket]] = {}
    chats_put_websockets: dict[int, set[fastapi.WebSocket]] = {}
    chats_delete_websockets: dict[int, set[fastapi.WebSocket]] = {}

    # dict[User.id, dict[Chat.id, set[fastapi.WebSocket]]]
    chat_memberships_post_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    chat_memberships_put_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    chat_memberships_delete_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

    chat_last_message_update_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

    async def chats_post_update(
        self,
        chat_data: ChatPubsubModel,
        is_post: bool):

        message_receivers_list: Sequence[int] = chat_data.receivers
        
        for receiver_id in message_receivers_list:
            websockets_container: dict[int, set[fastapi.WebSocket]]

            if is_post:
                websockets_container = self.chats_post_websockets
            else:
                websockets_container = self.chats_put_websockets

            for websocket in websockets_container.get(receiver_id, set()):
                chat_response_model: ChatResponseModel = ChatResponseModel(
                id = chat_data.id,
                chat_kind = chat_data.chat_kind,
                name = chat_data.name,
                owner_user_id = chat_data.owner_user_id,
                date_and_time_created = chat_data.date_and_time_created,
                has_avatar = False,
                last_message = None)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_response_model))


    async def chats_delete(
        self,
        chat_data: ChatPubsubModel):

        message_receivers_list: Sequence[int] = chat_data.receivers

        for receiver_id in message_receivers_list:
            for websocket in self.chats_delete_websockets.get(receiver_id, set()):
                chat_response_model: ChatResponseModel = ChatResponseModel(
                    id=chat_data.id,
                    chat_kind=chat_data.chat_kind,
                    name=chat_data.name,
                    owner_user_id=chat_data.owner_user_id,
                    date_and_time_created=chat_data.date_and_time_created,
                    has_avatar=False,
                    last_message=None)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_response_model))


    async def chat_memberships_post_update(
        self,
        chat_membership_data: ChatMembershipPubsubModel,
        is_post: bool):

        message_receivers_list: Sequence[int] = chat_membership_data.receivers

        for receiver_id in message_receivers_list:
            websockets_container: dict[int, dict[int, set[fastapi.WebSocket]]]

            if is_post:
                websockets_container = self.chat_memberships_post_websockets
            else:
                websockets_container = self.chat_memberships_put_websockets

            for websocket in websockets_container.get(receiver_id, dict()).get(chat_membership_data.chat_id, set()):
                chat_membership_model: ChatMembershipResponseModel = ChatMembershipResponseModel(
                    id = chat_membership_data.id,
                    chat_id = chat_membership_data.chat_id,
                    chat_user_id = chat_membership_data.chat_user_id,
                    date_and_time_added = chat_membership_data.date_and_time_added,
                    chat_role = chat_membership_data.chat_role)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_membership_model))


    async def chat_memberships_delete(
        self,
        chat_membership_data: ChatMembershipPubsubModel):

        message_receivers_list: Sequence[int] = chat_membership_data.receivers

        for receiver_id in message_receivers_list:
            for websocket in self.chat_memberships_delete_websockets.get(receiver_id, dict()).get(chat_membership_data.chat_id, set()):
                chat_membership_model: ChatMembershipResponseModel = ChatMembershipResponseModel(
                    id=chat_membership_data.id,
                    chat_id=chat_membership_data.chat_id,
                    chat_user_id=chat_membership_data.chat_user_id,
                    date_and_time_added=chat_membership_data.date_and_time_added,
                    chat_role=chat_membership_data.chat_role)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_membership_model))


    async def chat_last_message_update(
        self,
        chat_message_data: LastMessagePubsubWebsocketModel,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = chat_message_data.receivers

        for receiver_id in message_receivers_list:
            if chat_message_data.message:
                if chat_message_data.message.sender_user_id == receiver_id:
                    selected_message: Message | None = ((await db.execute(
                    sqlalchemy.select(Message)
                    .where(Message.id == chat_message_data.message.id)))
                    .scalars().first())

                    receiver_user: User | None = (await db.execute(
                    sqlalchemy.select(User)
                    .where(User.id == receiver_id))).scalars().first()

                    if selected_message and receiver_user:
                        chat_message_data.message.is_read = await backend.routers.messages.utils.is_message_read(selected_message, receiver_user, db)

            for websocket in self.chat_last_message_update_websockets.get(receiver_id, dict()).get(chat_message_data.chat_id, set()):
                last_message_model: LastMessageResponseModel = LastMessageResponseModel(message = None)
                if chat_message_data.message:
                    last_message_model.message = MessageResponseModel(
                    id = chat_message_data.message.id,
                    chat_id = chat_message_data.message.chat_id,
                    sender_user_id = chat_message_data.message.sender_user_id,
                    date_and_time_sent = chat_message_data.message.date_and_time_sent,
                    date_and_time_edited = chat_message_data.message.date_and_time_edited,
                    message_text = chat_message_data.message.message_text,
                    reply_message_id = chat_message_data.message.reply_message_id,
                    parent_message_id = chat_message_data.message.parent_message_id,
                    is_read = chat_message_data.message.is_read)

                await websocket.send_json(fastapi.encoders.jsonable_encoder(last_message_model))


    async def get_chats_websocket_dict(self, websocket_type: WebsocketType) -> dict[int, set[fastapi.WebSocket]]:
        websockets_dict: dict[int, set[fastapi.WebSocket]] = {}

        match websocket_type:
            case WebsocketType.CHAT_POST:
                websockets_dict = self.chats_post_websockets
            case WebsocketType.CHAT_PUT:
                websockets_dict = self.chats_put_websockets
            case WebsocketType.CHAT_DELETE:
                websockets_dict = self.chats_delete_websockets

        return websockets_dict


    async def get_memberships_websocket_dict(self, websocket_type: WebsocketType) -> dict[int, dict[int, set[fastapi.WebSocket]]]:
        websockets_dict: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

        match websocket_type:
            case WebsocketType.CHAT_MEMBERSHIP_POST:
                websockets_dict = self.chat_memberships_post_websockets
            case WebsocketType.CHAT_MEMBERSHIP_PUT:
                websockets_dict = self.chat_memberships_put_websockets
            case WebsocketType.CHAT_MEMBERSHIP_DELETE:
                websockets_dict = self.chat_memberships_delete_websockets

        return websockets_dict


    async def add_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_user_id: int,
        websocket_type: WebsocketType,
        selected_chat_id: int | None = None):

        await websocket.accept()

        if websocket_type in [WebsocketType.CHAT_POST, WebsocketType.CHAT_PUT, WebsocketType.CHAT_DELETE]:
            websockets_list: dict[int, set[fastapi.WebSocket]] = await self.get_chats_websocket_dict(websocket_type)

            if not websockets_list.get(selected_user_id, None):
                websockets_list[selected_user_id] = set()

            websockets_list[selected_user_id].add(websocket)

        elif websocket_type in [WebsocketType.CHAT_MEMBERSHIP_POST, WebsocketType.CHAT_MEMBERSHIP_PUT, WebsocketType.CHAT_MEMBERSHIP_DELETE, WebsocketType.CHAT_LAST_MESSAGE_UPDATE] and selected_chat_id is not None:
            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]]
            if websocket_type == WebsocketType.CHAT_LAST_MESSAGE_UPDATE:
                websockets_list = self.chat_last_message_update_websockets
            else:
                websockets_list = await self.get_memberships_websocket_dict(websocket_type)

            if not websockets_list.get(selected_user_id, None):
                websockets_list[selected_user_id] = dict()

            if not websockets_list.get(selected_user_id, dict()).get(selected_chat_id, set()):
                websockets_list[selected_user_id][selected_chat_id] = set()

            websockets_list[selected_user_id][selected_chat_id].add(websocket)


    async def remove_websocket(
        self,
        websocket: fastapi.WebSocket,
        selected_user_id: int,
        websocket_type: WebsocketType,
        selected_chat_id: int | None = None):

        if websocket_type in [WebsocketType.CHAT_POST, WebsocketType.CHAT_PUT, WebsocketType.CHAT_DELETE]:
            websockets_list: dict[int, set[fastapi.WebSocket]] = await self.get_chats_websocket_dict(websocket_type)

            if selected_user_id not in websockets_list:
                return

            websockets_list.get(selected_user_id, set()).discard(websocket)

            if len(websockets_list[selected_user_id]) == 0:
                websockets_list.pop(selected_user_id)

        elif websocket_type in [WebsocketType.CHAT_MEMBERSHIP_POST, WebsocketType.CHAT_MEMBERSHIP_PUT, WebsocketType.CHAT_MEMBERSHIP_DELETE, WebsocketType.CHAT_LAST_MESSAGE_UPDATE] and selected_chat_id is not None:
            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]]
            if websocket_type == WebsocketType.CHAT_LAST_MESSAGE_UPDATE:
                websockets_list = self.chat_last_message_update_websockets
            else:
                websockets_list = await self.get_memberships_websocket_dict(websocket_type)

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