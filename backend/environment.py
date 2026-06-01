import os

import dotenv

dotenv.load_dotenv()

# ВАЖНО: реальные секреты (пароли БД/Redis/MinIO, пароль SMTP, адрес почты)
# в исходный код НЕ зашиваются. Значения по умолчанию ниже — это безопасные
# плейсхолдеры только для локальной разработки. В продакшене все значения
# обязательно задаются через переменные окружения (.env / docker-compose),
# см. .env.example.

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
REDIS_DB = os.getenv("REDIS_DB", "0")

MINIO_USERS_AVATARS_BUCKET = os.getenv("MINIO_USERS_AVATARS_BUCKET", "usersavatars")
MINIO_CHATS_AVATARS_BUCKET = os.getenv("MINIO_CHATS_AVATARS_BUCKET", "chatsavatars")
MINIO_MESSAGES_ATTACHMENTS_BUCKET = os.getenv("MINIO_MESSAGES_ATTACHMENTS_BUCKET", "messagesattachments")


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

_cors_origins = os.getenv("FRONTEND_ORIGINS")
if _cors_origins:
    FRONTEND_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
else:
    FRONTEND_ORIGINS = [FRONTEND_URL]

BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")

# Единый адрес администратора. Если SMTP_FROM/SMTP_USERNAME не заданы
# отдельно, они берутся из ADMIN_EMAIL — так в .env достаточно указать
# один адрес (см. .env.example). docker-compose.yaml тоже прокидывает
# их явно, но фолбэк нужен, когда бэкенд запускается напрямую.
_admin_email = os.getenv("ADMIN_EMAIL", "")

# Реквизиты SMTP берутся ТОЛЬКО из окружения. Пустые значения по умолчанию
# означают «почта не настроена» — отправка письма аккуратно завершится
# ошибкой email_delivery_error, секреты в коде/Git не хранятся.
SMTP_HOSTNAME = os.getenv("SMTP_HOSTNAME", "")
SMTP_USERNAME = os.getenv("SMTP_USERNAME") or _admin_email
SMTP_FROM = os.getenv("SMTP_FROM") or _admin_email
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

SERVICE_PUBLIC_NAME = os.getenv("SERVICE_PUBLIC_NAME", "Мессенджер")
