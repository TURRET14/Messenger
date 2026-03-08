import fastapi
import fastapi.encoders
import redis.asyncio
import sqlalchemy.orm
from typing import Sequence

from backend.routers.chats.models import ChatUserWithReceiversModel
from models import *
from backend.storage import *

class MessagesWebsocketConnectionManager:
    messages_post_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}
    messages_put_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}
    messages_delete_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}

    message_read_post_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}

    async def messages_post_update(
        self,
        message_data: MessageIDWithChatIDWithReceiversModel,
        is_post: bool,
        db: sqlalchemy.orm.session.Session):

        message_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).where(User.id.in_(message_data.receivers))).scalars().all()

        for receiver in message_receivers_list:
            websockets_container: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}

            if is_post:
                websockets_container = self.messages_post_websockets
            else:
                websockets_container = self.messages_put_websockets

            for websocket in websockets_container[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_data.chat_id)).scalars().first()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_data))


    async def messages_delete(
        self,
        message_data: MessageIDWithChatIDWithReceiversModel,
        db: sqlalchemy.orm.session.Session):

        message_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).where(User.id.in_(message_data.receivers))).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.messages_delete_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_data.chat_id)).scalars().first()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_data))


    async def message_read_mark_post(
        self,
        message_read_mark_data: ReadMarkData,
        db: sqlalchemy.orm.session.Session):

        message_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).where(User.id.in_(message_read_mark_data.receivers))).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.message_read_post_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_read_mark_data.chat_id)).scalars().first()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(MessageReadMarkResponseModel(
                id = message_read_mark_data.id,
                chat_id = message_read_mark_data.chat_id,
                message_id = message_read_mark_data.message_id,
                reader_id = message_read_mark_data.reader_id)))


messages_websocket_connection_manager_instance: MessagesWebsocketConnectionManager = MessagesWebsocketConnectionManager()

async def get_messages_websocket_connection_manager():
    return messages_websocket_connection_manager_instance