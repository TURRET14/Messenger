import fastapi
import fastapi.encoders
import redis
import sqlalchemy.orm
from typing import Sequence

from models import *

from backend.storage import *

class MessagesWebsocketConnectionManager:
    messages_post_websockets: dict[User, set[fastapi.WebSocket]] = {}
    messages_put_websockets: dict[User, set[fastapi.WebSocket]] = {}
    messages_delete_websockets: dict[User, set[fastapi.WebSocket]] = {}

    async def messages_post_update(
        self,
        message_id: int,
        is_post: bool,
        db: sqlalchemy.orm.session.Session):

        selected_message: Message = db.execute(sqlalchemy.select(Message).where(Message.id == message_id)).scalars().first()

        if not selected_message:
            return

        message_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == selected_message.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .where(ChatUser.is_active == True)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        sender: User = db.execute(sqlalchemy.select(User).where(User.id == selected_message.sender_user_id)).scalars().first()

        if not sender:
            sender = User()

        for receiver in message_receivers_list:

            websockets_container: dict[User, set[fastapi.WebSocket]]

            if is_post:
                websockets_container = self.messages_post_websockets
            else:
                websockets_container = self.messages_put_websockets

            for websocket in websockets_container[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(MessageResponseModel(
                id = selected_message.id,
                chat_id = selected_message.chat_id,
                date_and_time_sent = selected_message.date_and_time_sent,
                date_and_time_edited = selected_message.date_and_time_edited,
                message_text = selected_message.message_text,
                sender_id = selected_message.sender_user_id,
                sender_username = sender.username,
                sender_name = sender.name,
                sender_surname = sender.surname,
                sender_second_name = sender.second_name,
                reply_message_id = selected_message.reply_message_id)))


    async def messages_delete(
        self,
        message_data: MessageDeleteModel,
        db: sqlalchemy.orm.session.Session):

        message_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == message_data.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .where(ChatUser.is_active == True)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.messages_delete_websockets[receiver]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(MessageDeleteModel(
                id = message_data.id,
                chat_id = message_data.chat_id)))


messages_websocket_connection_manager_instance: MessagesWebsocketConnectionManager = MessagesWebsocketConnectionManager()

async def get_messages_websocket_connection_manager():
    return messages_websocket_connection_manager_instance