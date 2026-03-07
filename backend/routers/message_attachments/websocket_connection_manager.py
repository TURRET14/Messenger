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
        message_attachment_data: MessageAttachmentModelWithReceivers,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(message_attachment_data.receivers))).scalars().all():
            for websocket in self.message_attachments_post_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_attachment_data.chat_id)).scalar()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(MessageAttachmentModel(
                id = message_attachment_data.id,
                chat_id = message_attachment_data.chat_id,
                message_id = message_attachment_data.message_id)))


    async def message_attachments_delete(
        self,
        message_attachment_data: MessageAttachmentModelWithReceivers,
        db: sqlalchemy.orm.session.Session):

        for receiver in db.execute(sqlalchemy.select(User).where(User.id.in_(message_attachment_data.receivers))).scalars().all():
            for websocket in self.message_attachments_delete_websockets[receiver][db.execute(sqlalchemy.select(Chat).where(Chat.id == message_attachment_data.chat_id)).scalar()]:
                await websocket.send_json(fastapi.encoders.jsonable_encoder(MessageAttachmentModel(id = message_attachment_data.id,
                chat_id = message_attachment_data.chat_id,
                message_id = message_attachment_data.message_id)))


message_attachments_websocket_connection_manager_instance: MessageAttachmentsWebsocketConnectionManager = MessageAttachmentsWebsocketConnectionManager()

async def get_websocket_connection_manager():
    return message_attachments_websocket_connection_manager_instance