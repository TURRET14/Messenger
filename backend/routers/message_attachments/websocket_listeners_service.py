import json
import redis
import sqlalchemy.orm
import asyncio

from models import *
import websocket_connection_manager


async def websocket_message_attachments_post_subscriber(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("message_attachments_post")
    for selected_message_attachment_data in pubsub.listen():
        message_attachment_data: MessageAttachmentModel = MessageAttachmentModel.model_validate(json.loads(selected_message_attachment_data))
        asyncio.create_task(messages_websocket_connection_manager.message_attachments_post(message_attachment_data, db))


async def websocket_message_attachments_delete_subscriber(
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis,
    messages_websocket_connection_manager: websocket_connection_manager.MessageAttachmentsWebsocketConnectionManager):

    pubsub = redis_client.pubsub()
    pubsub.subscribe("message_attachments_delete")
    for selected_message_attachment_data in pubsub.listen():
        message_attachment_data = MessageAttachmentModel.model_validate(json.loads(selected_message_attachment_data))
        asyncio.create_task(messages_websocket_connection_manager.message_attachments_delete(message_attachment_data, db))