import fastapi
import fastapi.encoders
import sqlalchemy.orm

from models import *
from backend.routers.common_models import *
from backend.storage import *

class ChatsWebsocketConnectionManager:
    chats_post_websockets: dict[User, set[fastapi.WebSocket]] = {}
    chats_put_websockets: dict[User, set[fastapi.WebSocket]] = {}
    chats_delete_websockets: dict[User, set[fastapi.WebSocket]] = {}

    chat_users_post_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}
    chat_users_put_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}
    chat_users_delete_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}

    async def chats_post_update(
        self,
        chat_with_receivers: ChatWithReceiversModel,
        is_post: bool,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(chat_with_receivers.receivers))).scalars().all():
            websockets_container: dict[User, set[fastapi.WebSocket]]

            if is_post:
                websockets_container = self.chats_post_websockets
            else:
                websockets_container = self.chats_put_websockets

            for websocket in websockets_container[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(ChatIDModelWithAvatarData(
                id = chat_with_receivers.chat_id,
                is_avatar_changed = chat_with_receivers.is_avatar_changed)))


    async def chats_delete(
        self,
        chat_with_receivers: ChatWithReceiversModel,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(chat_with_receivers.receivers))).scalars().all():
            for websocket in self.chats_delete_websockets[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(ChatIDModelWithAvatarData(
                id = chat_with_receivers.chat_id,
                is_avatar_changed = chat_with_receivers.is_avatar_changed)))


    async def chat_users_post_update(
        self,
        chat_user_with_receivers: ChatUserWithReceiversModel,
        is_post: bool,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(chat_user_with_receivers.receivers))).scalars().all():
            websockets_container: dict[User, dict[Chat, set[fastapi.WebSocket]]]

            if is_post:
                websockets_container = self.chat_users_post_websockets
            else:
                websockets_container = self.chat_users_put_websockets

            for websocket in websockets_container[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == chat_user_with_receivers.chat_id)).scalars().first()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(IDModel(
                id = chat_user_with_receivers.id)))


    async def chat_users_delete(
        self,
        chat_user_with_receivers: ChatUserWithReceiversModel,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(chat_user_with_receivers.receivers))).scalars().all():
            for websocket in self.chat_users_delete_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == chat_user_with_receivers.chat_id)).scalars().first()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(IDModel(
                id = chat_user_with_receivers.id)))


chats_websocket_connection_manager_instance: ChatsWebsocketConnectionManager = ChatsWebsocketConnectionManager()

async def get_chats_websocket_connection_manager():
    return chats_websocket_connection_manager_instance