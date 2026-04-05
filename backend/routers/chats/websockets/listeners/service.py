import redis.asyncio

from backend.storage import *
from backend.routers.chats.websockets.connection_manager import (WebsocketConnectionManager)
from backend.routers.chats.websockets.models import (ChatMembershipPubsubModel, ChatPubsubModel, ChatWithReceiversPubsubDeleteModel)


async def websocket_chats_post_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHATS_POST)
            async for selected_chat_data in pubsub_subscription.listen():
                if selected_chat_data["type"] != "message":
                    continue
                selected_chat_data = selected_chat_data["data"]

                selected_chat_model: ChatPubsubModel = ChatPubsubModel.model_validate_json(selected_chat_data)
                async with async_session_maker() as db:
                    await chats_websocket_connection_manager.chats_post_update(selected_chat_model, True, db)
        except Exception:
            pass


async def websocket_chats_put_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHATS_PUT)
            async for selected_chat_data in pubsub_subscription.listen():
                if selected_chat_data["type"] != "message":
                    continue

                selected_chat_data = selected_chat_data["data"]

                selected_chat_model: ChatPubsubModel = ChatPubsubModel.model_validate_json(selected_chat_data)
                async with async_session_maker() as db:
                    await chats_websocket_connection_manager.chats_post_update(selected_chat_model, False, db)
        except Exception:
            pass


async def websocket_chats_delete_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHATS_DELETE)
            async for selected_chat_with_receivers_data in pubsub_subscription.listen():
                if selected_chat_with_receivers_data["type"] != "message":
                    continue

                selected_chat_with_receivers_data = selected_chat_with_receivers_data["data"]

                chat_with_receivers_model: ChatWithReceiversPubsubDeleteModel = ChatWithReceiversPubsubDeleteModel.model_validate_json(selected_chat_with_receivers_data)
                await chats_websocket_connection_manager.chats_delete(chat_with_receivers_model)
        except Exception:
            pass


async def websocket_chat_memberships_post_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHAT_MEMBERSHIPS_POST)
            async for selected_chat_membership_data in pubsub_subscription.listen():
                if selected_chat_membership_data["type"] != "message":
                    continue

                selected_chat_membership_data = selected_chat_membership_data["data"]

                selected_chat_membership_model: ChatMembershipPubsubModel = ChatMembershipPubsubModel.model_validate_json(selected_chat_membership_data)
                async with async_session_maker() as db:
                    await chats_websocket_connection_manager.chat_memberships_post_update(selected_chat_membership_model,True, db)
        except Exception:
            pass


async def websocket_chat_memberships_put_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHAT_MEMBERSHIPS_PUT)
            async for selected_chat_membership_data in pubsub_subscription.listen():
                if selected_chat_membership_data["type"] != "message":
                    continue

                selected_chat_membership_data = selected_chat_membership_data["data"]

                selected_chat_membership_model: ChatMembershipPubsubModel = ChatMembershipPubsubModel.model_validate_json(selected_chat_membership_data)
                async with async_session_maker() as db:
                    await chats_websocket_connection_manager.chat_memberships_post_update(selected_chat_membership_model,False, db)
        except Exception:
            pass


async def websocket_chat_memberships_delete_listener(
    redis_client: RedisClient,
    chats_websocket_connection_manager: WebsocketConnectionManager):

    while True:
        try:
            pubsub_subscription: redis.asyncio.client.PubSub = await redis_client.pubsub_subscribe(RedisPubsubChannel.CHAT_MEMBERSHIPS_DELETE)
            async for selected_chat_membership_data in pubsub_subscription.listen():
                if selected_chat_membership_data["type"] != "message":
                    continue

                selected_chat_membership_data = selected_chat_membership_data["data"]

                selected_chat_membership_model: ChatMembershipPubsubModel = ChatMembershipPubsubModel.model_validate_json(selected_chat_membership_data)
                async with async_session_maker() as db:
                    await chats_websocket_connection_manager.chat_memberships_delete(selected_chat_membership_model, db)
        except Exception:
            pass