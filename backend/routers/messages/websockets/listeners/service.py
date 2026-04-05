import redis.asyncio
import asyncio
from backend.storage import *

from backend.routers.messages.websockets.models import (MessagePubsubWebsocketModel, ReadMarkPubsubWebsocketModel)
from backend.routers.messages.websockets.connection_manager import (WebsocketConnectionManager)


async def websocket_messages_post_listener(
    redis_client: RedisClient,
    connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(
                RedisPubsubChannel.MESSAGES_POST)
            async for selected_message_data in pubsub_subscription.listen():
                if selected_message_data["type"] != "message":
                    continue

                selected_message_data = selected_message_data["data"]

                selected_message_data_model: MessagePubsubWebsocketModel = MessagePubsubWebsocketModel.model_validate_json(
                    selected_message_data)
                async with async_session_maker() as db:
                    asyncio.create_task(connection_manager.messages_post_update(selected_message_data_model, True, db))
        except Exception:
            pass


async def websocket_messages_put_listener(
    redis_client: RedisClient,
    connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(
                RedisPubsubChannel.MESSAGES_PUT)
            async for selected_message_data in pubsub_subscription.listen():
                if selected_message_data["type"] != "message":
                    continue

                selected_message_data = selected_message_data["data"]

                selected_message_data_model: MessagePubsubWebsocketModel = MessagePubsubWebsocketModel.model_validate_json(
                    selected_message_data)
                async with async_session_maker() as db:
                    asyncio.create_task(connection_manager.messages_post_update(selected_message_data_model, False, db))
        except Exception:
            pass


async def websocket_messages_delete_listener(
    redis_client: RedisClient,
    connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.MESSAGES_DELETE)
            async for selected_message_data in pubsub_subscription.listen():
                if selected_message_data["type"] != "message":
                    continue

                selected_message_data = selected_message_data["data"]

                selected_message_data_model: MessagePubsubWebsocketModel = MessagePubsubWebsocketModel.model_validate_json(selected_message_data)
                async with async_session_maker() as db:
                    asyncio.create_task(connection_manager.messages_delete(selected_message_data_model, db))
        except Exception:
            pass


async def websocket_messages_read_mark_post_listener(
    redis_client: RedisClient,
    connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.MESSAGES_READ_POST)
            async for selected_message_read_mark_data in pubsub_subscription.listen():
                if selected_message_read_mark_data["type"] != "message":
                    continue

                selected_message_read_mark_data = selected_message_read_mark_data["data"]

                selected_message_read_mark_data_model: ReadMarkPubsubWebsocketModel = ReadMarkPubsubWebsocketModel.model_validate_json(selected_message_read_mark_data)
                async with async_session_maker() as db:
                    asyncio.create_task(connection_manager.message_read_mark_post(selected_message_read_mark_data_model, db))
        except Exception:
            pass
