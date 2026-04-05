import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
import enum
from typing import Sequence

from backend.routers.chats.websockets import utils
from backend.routers.chats.websockets.models import (ChatMembershipPubsubModel, ChatPubsubModel, ChatWithReceiversPubsubDeleteModel)
from backend.routers.common_models import (IDModel)


class WebsocketType(enum.Enum):
    CHAT_POST = "CHAT_POST"
    CHAT_PUT = "CHAT_PUT"
    CHAT_DELETE = "CHAT_DELETE"
    
    CHAT_MEMBERSHIP_POST = "CHAT_MEMBERSHIP_POST"
    CHAT_MEMBERSHIP_PUT = "CHAT_MEMBERSHIP_PUT"
    CHAT_MEMBERSHIP_DELETE = "CHAT_MEMBERSHIP_DELETE"


class WebsocketConnectionManager:
    # dict[User.id, set[fastapi.WebSocket]]
    chats_post_websockets: dict[int, set[fastapi.WebSocket]] = {}
    chats_put_websockets: dict[int, set[fastapi.WebSocket]] = {}
    chats_delete_websockets: dict[int, set[fastapi.WebSocket]] = {}

    # dict[User.id, dict[Chat.id, set[fastapi.WebSocket]]]
    chat_memberships_post_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    chat_memberships_put_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}
    chat_memberships_delete_websockets: dict[int, dict[int, set[fastapi.WebSocket]]] = {}

    async def chats_post_update(
        self,
        chat_data: ChatPubsubModel,
        is_post: bool,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(chat_data.id, db)
        
        for receiver_id in message_receivers_list:
            websockets_container: dict[int, set[fastapi.WebSocket]]

            if is_post:
                websockets_container = self.chats_post_websockets
            else:
                websockets_container = self.chats_put_websockets

            for websocket in websockets_container.get(receiver_id, set()):
                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_data))


    async def chats_delete(
        self,
        chat_data: ChatWithReceiversPubsubDeleteModel):

        message_receivers_list: Sequence[int] = chat_data.receivers

        for receiver_id in message_receivers_list:
            for websocket in self.chats_delete_websockets.get(receiver_id, set()):
                await websocket.send_json(fastapi.encoders.jsonable_encoder(IDModel(id = chat_data.id)))


    async def chat_memberships_post_update(
        self,
        chat_membership_data: ChatMembershipPubsubModel,
        is_post: bool,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(chat_membership_data.chat_id, db)

        for receiver_id in message_receivers_list:
            websockets_container: dict[int, dict[int, set[fastapi.WebSocket]]]

            if is_post:
                websockets_container = self.chat_memberships_post_websockets
            else:
                websockets_container = self.chat_memberships_put_websockets

            for websocket in websockets_container.get(receiver_id, dict()).get(chat_membership_data.chat_id, set()):
                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_membership_data))


    async def chat_memberships_delete(
        self,
        chat_membership_data: ChatMembershipPubsubModel,
        db: sqlalchemy.ext.asyncio.AsyncSession):

        message_receivers_list: Sequence[int] = await utils.get_chat_user_ids(chat_membership_data.chat_id, db)

        for receiver_id in message_receivers_list:
            for websocket in self.chat_memberships_delete_websockets.get(receiver_id, dict()).get(chat_membership_data.chat_id, set()):
                await websocket.send_json(fastapi.encoders.jsonable_encoder(chat_membership_data))


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

        elif websocket_type in [WebsocketType.CHAT_MEMBERSHIP_POST, WebsocketType.CHAT_MEMBERSHIP_PUT, WebsocketType.CHAT_MEMBERSHIP_DELETE] and selected_chat_id is not None:
            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = await self.get_memberships_websocket_dict(websocket_type)

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

        elif websocket_type in [WebsocketType.CHAT_MEMBERSHIP_POST, WebsocketType.CHAT_MEMBERSHIP_PUT, WebsocketType.CHAT_MEMBERSHIP_DELETE] and selected_chat_id is not None:

            websockets_list: dict[int, dict[int, set[fastapi.WebSocket]]] = await self.get_memberships_websocket_dict(websocket_type)

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