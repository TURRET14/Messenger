import os

import dotenv

dotenv.load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "messenger_db")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minio")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")


REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


FRONTEND_URL = os.getenv("FRONTEND_URL", "localhost:3000")
BACKEND_PORT = os.getenv("BACKEND_PORT", "3000")