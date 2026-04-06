import dataclasses
import enum

import fastapi
import redis.asyncio
import asyncio
import secrets
import datetime

from backend.routers.messages.websockets.models import (MessagePubsubWebsocketModel, ReadMarkPubsubWebsocketModel,
                                                        LastMessagePubsubWebsocketModel)
from backend.routers.chats.websockets.models import (ChatMembershipPubsubModel, ChatPubsubModel, ChatPubsubModel)

import backend.routers.parameters as parameters
from backend.routers.errors import ErrorRegistry
import backend.environment as environment


@dataclasses.dataclass()
class SessionModel:
    session_id: str
    user_id: int
    user_agent: str
    creation_datetime: int
    expiration_datetime: int


class RedisPubsubChannel(enum.Enum):
    MESSAGES_POST = "MESSAGES_POST"
    MESSAGES_PUT = "MESSAGES_PUT"
    MESSAGES_DELETE = "MESSAGES_DELETE"
    MESSAGES_READ_POST = "MESSAGES_READ_POST"

    CHATS_POST = "CHATS_POST"
    CHATS_PUT = "CHATS_PUT"
    CHATS_DELETE = "CHATS_DELETE"

    CHAT_MEMBERSHIPS_POST = "CHAT_MEMBERSHIPS_POST"
    CHAT_MEMBERSHIPS_PUT = "CHAT_MEMBERSHIPS_PUT"
    CHAT_MEMBERSHIPS_DELETE = "CHAT_MEMBERSHIPS_DELETE"

    CHAT_LAST_MESSAGE_UPDATE = "CHAT_LAST_MESSAGE_UPDATE"


class RedisClient:
    def __init__(self, host, port, password):
        self.client = redis.asyncio.Redis(host = host, port = port, password = password, decode_responses = True)

    async def create_user_session(self, user_id: int, user_agent: str) -> str:
        session_id = secrets.token_urlsafe(64)
        creation_datetime: int = int(datetime.datetime.now().timestamp())
        expiration_datetime: int = creation_datetime + int(datetime.timedelta(seconds = parameters.REDIS_USER_SESSION_EXPIRATION_TIME_SECONDS).total_seconds())

        coroutines: list = list()
        coroutines.append(self.client.sadd(f"user:{user_id}:sessions", session_id))
        coroutines.append(self.client.hset(f"session:{session_id}:data",
        mapping = {"user_id": user_id, "user_agent": user_agent, "creation_datetime": creation_datetime, "expiration_datetime": expiration_datetime}))
        coroutines.append(self.client.expireat(f"user:{user_id}:sessions", expiration_datetime))
        coroutines.append(self.client.expireat(f"session:{session_id}:data", expiration_datetime))

        await asyncio.gather(*coroutines)

        return session_id


    async def get_all_user_session_ids(self, user_id: int) -> set[str]:
        return await self.client.smembers(f"user:{user_id}:sessions")


    async def get_user_session_data(self, session_id: str) -> SessionModel:
        if not await self.client.exists(f"session:{session_id}:data"):
            raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_session_error.error_status_code, detail = ErrorRegistry.invalid_session_error)

        session_dict: dict[str, str] = await self.client.hgetall(f"session:{session_id}:data")
        session: SessionModel = SessionModel(
        session_id = session_id,
        user_id = int(session_dict["user_id"]),
        user_agent = session_dict["user_agent"],
        creation_datetime = int(session_dict["creation_datetime"]),
        expiration_datetime = int(session_dict["expiration_datetime"]))

        return session


    async def get_all_user_sessions_data(self, user_id: int) -> list[SessionModel]:
        session_ids: set[str] = await self.client.smembers(f"user:{user_id}:sessions")
        sessions_data_list: list[SessionModel] = list()
        for session_id in session_ids:
            sessions_data_list.append(await self.get_user_session_data(session_id))

        return sessions_data_list


    async def delete_user_session(self, session_id: str):
        if await self.client.exists(f"session:{session_id}:data"):
            user_id: str | None = await self.client.hget(f"session:{session_id}:data", "user_id")
            if user_id:
                coroutines: list = list()
                coroutines.append(self.client.srem(f"user:{user_id}:sessions", session_id))
                coroutines.append(self.client.delete(f"session:{session_id}:data"))

                await asyncio.gather(*coroutines)


    async def delete_all_user_sessions(self, user_id: int):
        if await self.client.exists(f"user:{user_id}:sessions"):
            sessions_set: set[str] = await self.client.smembers(f"user:{user_id}:sessions")
            coroutines: list = list()
            coroutines.append(self.client.delete(f"user:{user_id}:sessions"))
            for session_id in sessions_set:
                coroutines.append(self.client.delete(f"session:{session_id}:data"))

            await asyncio.gather(*coroutines)


    async def pubsub_subscribe(self, subscription: RedisPubsubChannel) -> redis.asyncio.client.PubSub:
        pubsub: redis.asyncio.client.PubSub = self.client.pubsub()
        await pubsub.subscribe(subscription.value)

        return pubsub


    async def pubsub_publish(
        self,
        subscription: RedisPubsubChannel,
        data: MessagePubsubWebsocketModel | ReadMarkPubsubWebsocketModel | ChatPubsubModel | ChatPubsubModel | ChatMembershipPubsubModel | LastMessagePubsubWebsocketModel):
        await self.client.publish(subscription.value, data.model_dump_json())


    async def pubsub_publish_post_message(self, message: MessagePubsubWebsocketModel):
        await self.pubsub_publish(RedisPubsubChannel.MESSAGES_POST, message)


    async def pubsub_publish_put_message(self, message: MessagePubsubWebsocketModel):
        await self.pubsub_publish(RedisPubsubChannel.MESSAGES_PUT, message)


    async def pubsub_publish_delete_message(self, message: MessagePubsubWebsocketModel):
        await self.pubsub_publish(RedisPubsubChannel.MESSAGES_DELETE, message)


    async def pubsub_publish_message_read_post(self, message: ReadMarkPubsubWebsocketModel):
        await self.pubsub_publish(RedisPubsubChannel.MESSAGES_READ_POST, message)


    async def pubsub_publish_post_chat(self, chat: ChatPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHATS_POST, chat)


    async def pubsub_publish_put_chat(self, chat: ChatPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHATS_PUT, chat)


    async def pubsub_publish_delete_chat(self, chat: ChatPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHATS_DELETE, chat)


    async def pubsub_publish_post_chat_membership(self, chat_membership: ChatMembershipPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHAT_MEMBERSHIPS_POST, chat_membership)


    async def pubsub_publish_put_chat_membership(self, chat_membership: ChatMembershipPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHAT_MEMBERSHIPS_PUT, chat_membership)


    async def pubsub_publish_delete_chat_membership(self, chat_membership: ChatMembershipPubsubModel):
        await self.pubsub_publish(RedisPubsubChannel.CHAT_MEMBERSHIPS_DELETE, chat_membership)


    async def pubsub_publish_chat_last_message_update(self, chat_message_data: LastMessagePubsubWebsocketModel):
        await self.pubsub_publish(RedisPubsubChannel.CHAT_LAST_MESSAGE_UPDATE, chat_message_data)


redis_client: RedisClient = RedisClient(
    host = environment.REDIS_HOST,
    port = int(environment.REDIS_PORT),
    password = environment.REDIS_PASSWORD)


async def get_redis_client() -> RedisClient:
    return redis_client