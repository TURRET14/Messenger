import dataclasses
import os

import fastapi
import redis.asyncio
import asyncio
import secrets
import datetime

from django.conf.locale import fa

import backend.routers.parameters as parameters
from backend.routers.errors import ErrorRegistry


@dataclasses.dataclass()
class SessionModel:
    session_id: str
    user_id: int
    user_agent: str
    creation_datetime: int
    expiration_datetime: int


class RedisClient:
    def __init__(self, host, port, password):
        self.client = redis.asyncio.Redis(host = host, port = port, password = password, decode_responses = True)

    async def create_user_session(self, user_id: int, user_agent: str) -> str:
        session_id = secrets.token_urlsafe(64)
        creation_datetime: int = int(datetime.datetime.now().timestamp())
        expiration_datetime: int = creation_datetime + int(datetime.timedelta(seconds = parameters.redis_session_expiration_time_seconds).total_seconds())

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


redis_client: RedisClient = RedisClient("redis", os.getenv("REDIS_PORT"), os.getenv("REDIS_PASSWORD"))


async def get_redis_client() -> RedisClient:
    return redis_client