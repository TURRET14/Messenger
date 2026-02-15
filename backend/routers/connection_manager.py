import fastapi
import redis
import sqlalchemy.orm
from starlette.status import HTTP_404_NOT_FOUND

from backend.storage import *

class WebsocketConnectionManager:
    messages_post_websockets: dict[User, set[fastapi.WebSocket]] = {}
    messages_put_websockets: dict[User, set[fastapi.WebSocket]] = {}
    messages_delete_websockets: dict[User, set[fastapi.WebSocket]] = {}

    async def messages_post(self, message_id: int, db: sqlalchemy.orm.session.Session):

        selected_message: Message = db.execute(sqlalchemy.select(Message).where(Message.id == message_id)).scalars().first()

        if not selected_message:
            return

        message_receivers_list: sqlalchemy.Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == selected_message.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.messages_post_websockets[receiver]:
                await websocket.send_json({
                "id": selected_message.chat_id,
                "chat_id": selected_message.chat_id,
                "sender_user_id": selected_message.sender_user_id,
                "date_and_time_sent": selected_message.date_and_time_sent,
                "message_text": selected_message.message_text})


    async def messages_put(self, message_id: int, db: sqlalchemy.orm.session.Session):

        selected_message: Message = db.execute(sqlalchemy.select(Message).where(Message.id == message_id)).scalars().first()

        if not selected_message:
            return

        message_receivers_list: sqlalchemy.Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == selected_message.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.messages_put_websockets[receiver]:
                await websocket.send_json({
                "id": selected_message.chat_id,
                "chat_id": selected_message.chat_id,
                "sender_user_id": selected_message.sender_user_id,
                "date_and_time_sent": selected_message.date_and_time_sent,
                "message_text": selected_message.message_text})


    async def messages_delete(self, message_id: int, db: sqlalchemy.orm.session.Session):

        selected_message: Message = db.execute(sqlalchemy.select(Message).where(Message.id == message_id)).scalars().first()

        if not selected_message:
            return

        message_receivers_list: sqlalchemy.Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == selected_message.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in message_receivers_list:
            for websocket in self.messages_delete_websockets[receiver]:
                await websocket.send_json({
                "id": selected_message.chat_id,
                "chat_id": selected_message.chat_id})


websocket_connection_manager_instance: WebsocketConnectionManager = WebsocketConnectionManager()

async def get_websocket_connection_manager():
    return websocket_connection_manager_instance