import fastapi
import fastapi.encoders

from models import *
from backend.routers.common_models import *

from backend.storage import *

class ChatsWebsocketConnectionManager:
    chats_post_websockets: dict[User, set[fastapi.WebSocket]] = {}
    chats_put_websockets: dict[User, set[fastapi.WebSocket]] = {}
    chats_delete_websockets: dict[User, set[fastapi.WebSocket]] = {}

    async def chats_post_update(
        self,
        data: ChatWithReceiversModel,
        is_post: bool):

        for receiver in data.receivers:
            websockets_container: dict[User, set[fastapi.WebSocket]]

            if is_post:
                websockets_container = self.chats_post_websockets
            else:
                websockets_container = self.chats_put_websockets

            for websocket in websockets_container[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(ChatResponseModelWithAvatarData(
                id = data.chat.id,
                chat_kind = data.chat.chat_kind,
                name = data.chat.name,
                owner_user_id = data.chat.owner_user_id,
                date_and_time_created = data.chat.date_and_time_created,
                is_read_only = data.chat.is_read_only,
                is_avatar_changed = data.is_avatar_changed)))


    async def chats_delete(
        self,
        data: ChatWithReceiversModel):

        for receiver in data.receivers:
            for websocket in self.chats_delete_websockets[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(IDModel(id = data.chat.id)))


chats_websocket_connection_manager_instance: ChatsWebsocketConnectionManager = ChatsWebsocketConnectionManager()

async def get_chats_websocket_connection_manager():
    return chats_websocket_connection_manager_instance