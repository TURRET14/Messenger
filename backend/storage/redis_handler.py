import os
import redis

class RedisClient:
    def __init__(self, host, port, password):
        self.client = redis.asyncio.Redis(host = host, port = port, password = password, decode_responses = True)


redis_client: RedisClient = RedisClient("redis", os.getenv("REDIS_PORT"), os.getenv("REDIS_PASSWORD"))


def get_redis_client() -> redis.Redis:
    return redis_client.client