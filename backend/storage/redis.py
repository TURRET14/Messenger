import asyncio
import os
import secrets
from datetime import datetime, timedelta
import redis
import dotenv

import backend.parameters

dotenv.load_dotenv()




class RedisClient:
    def __init__(self, host, port, password):
        self.redis_handler = redis.asyncio.Redis(host=host, port=port, password=password, decode_responses=True)


    async def add_user_session(self, user_id: int, session_id: str = secrets.token_urlsafe(64), expiration_date: int = int(datetime.now().timestamp()) + int(timedelta(seconds = backend.parameters.redis_session_expiration_time_seconds).total_seconds())) -> None:
        coroutines: list = list()
        coroutines.append(self.redis_handler.sadd(f"user_id:{user_id}", session_id))
        coroutines.append(self.redis_handler.hset(f"session_id:{session_id}", mapping={"user_id": user_id, "expiration_date": expiration_date}))
        coroutines.append(self.redis_handler.expireat(f"user_id:{user_id}", expiration_date))
        coroutines.append(self.redis_handler.expireat(f"session_id:{session_id}", expiration_date))
        await asyncio.gather(*coroutines)


    async def remove_user_session(self, session_id: str) -> None:
        coroutines: list = list()
        coroutines.append(self.redis_handler.srem(f"user_id:{await self.redis_handler.hget(f"session_id:{session_id}", "user_id")}", session_id))
        coroutines.append(self.redis_handler.delete(f"session_id:{session_id}"))
        await asyncio.gather(*coroutines)


    async def clear_user_sessions(self, user_id: int) -> None:
        user_sessions: set = await self.redis_handler.smembers(f"user_id:{user_id}")
        coroutines: list = list()
        for session_id in user_sessions:
            coroutines.append(self.redis_handler.delete(f"session_id:{session_id}"))
        await asyncio.gather(*coroutines)
        await self.redis_handler.delete(f"user_id:{user_id}")


    async def get_session_data(self, session_id: str) -> dict[str, str]:
        return await self.redis_handler.hgetall(f"session_id:{session_id}")


redis_client: RedisClient = RedisClient("redis", os.getenv("REDIS_PORT"), os.getenv("REDIS_PASSWORD"))


def get_redis_client() -> RedisClient:
    return redis_client