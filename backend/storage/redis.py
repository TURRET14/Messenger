import os
from datetime import datetime, timedelta
import redis
import dotenv

import backend.parameters

dotenv.load_dotenv()




class RedisClient:
    def __init__(self, host, port, password):
        self.redis_handler = redis.asyncio.Redis(host=host, port=port, password=password)


    def add_user_session(self, user_id: int, session_id: str, expiration_date: datetime = datetime.now().timestamp() + timedelta(seconds=backend.parameters.redis_session_expiration_time_seconds).total_seconds()) -> None:
        self.redis_handler.sadd(f"user_id:${user_id}", session_id)
        self.redis_handler.hset(f"session_id:{session_id}", mapping={"user_id": user_id, "expiration_date": expiration_date})
        self.redis_handler.expireat(f"user_id:${user_id}", expiration_date)
        self.redis_handler.expireat(f"session_id:{session_id}", expiration_date)


    def remove_user_session(self, session_id: str) -> None:
        self.redis_handler.srem(f"user_id:${self.redis_handler.hget(f"session_id:{session_id}", "user_id")}", session_id)
        self.redis_handler.delete(f"session_id:{session_id}")


    def clear_user_sessions(self, user_id: int) -> None:
        self.redis_handler.delete(f"user_id:${user_id}")


    def get_session_data(self, session_id: str) -> dict[str, str]:
        return self.redis_handler.hgetall(f"session_id:{session_id}")


redis_client: RedisClient = RedisClient("redis", os.getenv("REDIS_PORT"), os.getenv("REDIS_PASSWORD"))


def get_redis_client() -> RedisClient:
    return redis_client