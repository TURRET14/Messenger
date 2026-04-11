import os

import dotenv

dotenv.load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "messenger_db")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minio_minio")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")

MINIO_USERS_AVATARS_BUCKET = os.getenv("MINIO_USERS_AVATARS_BUCKET", "usersavatars")
MINIO_CHATS_AVATARS_BUCKET = os.getenv("MINIO_CHATS_AVATARS_BUCKET", "chatsavatars")
MINIO_MESSAGES_ATTACHMENTS_BUCKET = os.getenv("MINIO_MESSAGES_ATTACHMENTS_BUCKET", "messagesattachments")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_PORT = os.getenv("BACKEND_PORT", "3000")

SMTP_HOSTNAME = os.getenv("SMTP_HOSTNAME", "smtp.yandex.ru")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "Messenger")
SMTP_FROM = os.getenv("SMTP_FROM", "Messenger")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "SMTP")

SERVICE_PUBLIC_NAME = os.getenv("SERVICE_PUBLIC_NAME", "Мессенджер")
