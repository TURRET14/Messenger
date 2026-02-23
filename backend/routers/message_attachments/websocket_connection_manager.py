from typing import Sequence

import fastapi
import fastapi.encoders
import sqlalchemy.orm

from backend.storage import *
from models import *

class MessageAttachmentsWebsocketConnectionManager:

    message_attachments_post_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}
    message_attachments_delete_websockets: dict[User, dict[Chat, set[fastapi.WebSocket]]] = {}

    async def message_attachments_post(
        self,
        message_attachment_data: MessageAttachmentModel,
        db: sqlalchemy.orm.session.Session):

        attachment_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == message_attachment_data.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in attachment_receivers_list:
            for websocket in self.message_attachments_post_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_attachment_data.chat_id)).scalar()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_attachment_data))


    async def message_attachments_delete(
        self,
        message_attachment_data: MessageAttachmentModel,
        db: sqlalchemy.orm.session.Session):


        attachment_receivers_list: Sequence[User] = db.execute(sqlalchemy.select(User).select_from(Chat)
        .where(Chat.id == message_attachment_data.chat_id)
        .join(ChatUser, ChatUser.chat_id == Chat.id)
        .join(User, User.id == ChatUser.chat_user_id)).scalars().all()

        for receiver in attachment_receivers_list:
            for websocket in self.message_attachments_delete_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_attachment_data.chat_id)).scalar()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(message_attachment_data))


message_attachments_websocket_connection_manager_instance: MessageAttachmentsWebsocketConnectionManager = MessageAttachmentsWebsocketConnectionManager()

async def get_websocket_connection_manager():
    return message_attachments_websocket_connection_manager_instance