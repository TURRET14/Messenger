import os
import redis.asyncio

class RedisClient:
    def __init__(self, host, port, password):
        self.client = redis.asyncio.Redis(host = host, port = port, password = password, decode_responses = True)


redis_client: RedisClient = RedisClient("redis", os.getenv("REDIS_PORT"), os.getenv("REDIS_PASSWORD"))


async def get_redis_client() -> redis.asyncio.Redis:
    return redis_client.client