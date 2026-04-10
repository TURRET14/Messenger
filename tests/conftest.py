import asyncio
import datetime
import os
from collections.abc import Awaitable, Generator
from typing import Any, TypeVar

import asyncpg
import fastapi
import minio
import pytest
import sqlalchemy
from fastapi.testclient import TestClient

os.environ["POSTGRES_DB"] = "messenger_test_db"
os.environ["REDIS_DB"] = "15"
os.environ["MINIO_USERS_AVATARS_BUCKET"] = "messenger-test-users-avatars"
os.environ["MINIO_CHATS_AVATARS_BUCKET"] = "messenger-test-chats-avatars"
os.environ["MINIO_MESSAGES_ATTACHMENTS_BUCKET"] = "messenger-test-messages-attachments"

import backend.storage as storage
from backend.email_service import EmailService
from backend.routers.chats.router import chats_router
from backend.routers.chats.websockets.websockets import chats_websockets
from backend.routers.messages.router import messages_router
from backend.routers.messages.websockets import websockets as messages_ws_module
from backend.routers.messages.websockets.websockets import messages_websockets_router
from backend.routers.message_attachments.router import message_attachments_router
from backend.routers.users.router import users_router
from backend.routers.chats.websockets import websockets as chats_ws_module
from backend.routers.security import hash_password
from backend.storage import database, minio_handler, redis_handler
from backend.storage.database import Base, Chat, ChatKind, ChatMembership, ChatRole, Friendship, FriendRequest, Message, MessageReceipt, User, UserBlock


_loop: asyncio.AbstractEventLoop | None = None
T = TypeVar("T")


def run_async(coro: Awaitable[T]) -> T:
    if _loop is None:
        raise RuntimeError("Тестовый event loop не инициализирован")
    return _loop.run_until_complete(coro)


TEST_DB_NAME = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis")
REDIS_DB = int(os.environ["REDIS_DB"])
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER = os.environ.get("MINIO_ROOT_USER", "minio")
MINIO_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minio_password")
TEST_DATABASE_URL = sqlalchemy.engine.URL.create(
    drivername="postgresql+asyncpg",
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=TEST_DB_NAME,
)


async def ensure_external_services_are_available() -> None:
    admin_connection = await asyncpg.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database="postgres",
    )
    await admin_connection.close()

    redis_client = redis_handler.RedisClient(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB)
    await redis_client.client.ping()
    await redis_client.client.aclose()

    minio.Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False).list_buckets()


async def recreate_test_database() -> None:
    admin_connection = await asyncpg.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database="postgres",
    )
    await admin_connection.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = $1 AND pid <> pg_backend_pid()
        """,
        TEST_DB_NAME,
    )
    await admin_connection.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    await admin_connection.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await admin_connection.close()


async def configure_database_engine() -> None:
    await database.db_engine.dispose()
    database.db_engine = sqlalchemy.ext.asyncio.create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        poolclass=sqlalchemy.pool.NullPool,
    )
    database.async_session_maker = sqlalchemy.ext.asyncio.async_sessionmaker(bind=database.db_engine, expire_on_commit=False)
    storage.async_session_maker = database.async_session_maker
    chats_ws_module.async_session_maker = database.async_session_maker
    messages_ws_module.async_session_maker = database.async_session_maker

    async with database.db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def truncate_database() -> None:
    async with database.async_session_maker() as db:
        table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
        await db.execute(sqlalchemy.text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        await db.commit()


async def clean_minio_objects() -> None:
    client = await minio_handler.get_minio_client()
    for bucket in minio_handler.MinioBucket:
        bucket_name = bucket.value
        if not client.client.bucket_exists(bucket_name):
            client.client.make_bucket(bucket_name)

        object_names = [item.object_name for item in client.client.list_objects(bucket_name, recursive=True)]
        for object_name in object_names:
            client.client.remove_object(bucket_name, object_name)


async def clean_redis() -> None:
    redis_client = await redis_handler.get_redis_client()
    await redis_client.client.flushdb()


@pytest.fixture(scope="session", autouse=True)
def integration_environment() -> Generator[None, None, None]:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    try:
        run_async(ensure_external_services_are_available())
    except Exception as exc:
        pytest.skip(f"Интеграционные тесты требуют запущенные Docker-сервисы Postgres/Redis/MinIO: {exc}")

    run_async(recreate_test_database())
    run_async(configure_database_engine())

    redis_handler.redis_client = redis_handler.RedisClient(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB)
    minio_handler.minio_client = minio_handler.MinioClient(MINIO_ENDPOINT, MINIO_USER, MINIO_PASSWORD)

    yield

    run_async(clean_redis())
    run_async(clean_minio_objects())
    run_async(database.db_engine.dispose())
    _loop.close()
    _loop = None


@pytest.fixture(autouse=True)
def isolate_test_state(integration_environment: None) -> Generator[None, None, None]:
    run_async(truncate_database())
    run_async(clean_redis())
    run_async(clean_minio_objects())
    yield
    run_async(truncate_database())
    run_async(clean_redis())
    run_async(clean_minio_objects())


@pytest.fixture
def email_outbox(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    sent_messages: list[dict[str, str]] = []

    async def fake_send_email_confirmation(receiver_email: str, code: str):
        sent_messages.append({"receiver_email": receiver_email, "code": code})

    monkeypatch.setattr(EmailService, "send_email_confirmation", staticmethod(fake_send_email_confirmation))
    return sent_messages


@pytest.fixture
def app(email_outbox: list[dict[str, str]]) -> fastapi.FastAPI:
    application = fastapi.FastAPI()
    application.include_router(users_router)
    application.include_router(chats_router)
    application.include_router(messages_router)
    application.include_router(message_attachments_router)
    application.include_router(chats_websockets)
    application.include_router(messages_websockets_router)

    @application.exception_handler(fastapi.exceptions.HTTPException)
    async def http_exception_handler(
        request: fastapi.Request,
        exception: fastapi.exceptions.HTTPException,
    ) -> fastapi.responses.JSONResponse:
        return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(exception.detail), status_code=exception.status_code)

    async def app_redis_client_dependency() -> redis_handler.RedisClient:
        return redis_handler.RedisClient(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB)

    async def app_minio_client_dependency() -> minio_handler.MinioClient:
        return minio_handler.MinioClient(MINIO_ENDPOINT, MINIO_USER, MINIO_PASSWORD)

    application.dependency_overrides[redis_handler.get_redis_client] = app_redis_client_dependency
    application.dependency_overrides[minio_handler.get_minio_client] = app_minio_client_dependency
    application.dependency_overrides[storage.get_redis_client] = app_redis_client_dependency
    application.dependency_overrides[storage.get_minio_client] = app_minio_client_dependency

    return application


@pytest.fixture
def client(app: fastapi.FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


class IntegrationHelper:
    def __init__(self, email_outbox: list[dict[str, str]]):
        self.email_outbox = email_outbox

    def run(self, coro: Awaitable[T]) -> T:
        return run_async(coro)

    async def create_user(
        self,
        *,
        username: str,
        name: str,
        surname: str,
        second_name: str | None,
        email_address: str,
        login: str,
        password: str,
        about: str | None = None,
        phone_number: str | None = None,
    ) -> User:
        async with database.async_session_maker() as db:
            user = User(
                username=username,
                name=name,
                surname=surname,
                second_name=second_name,
                email_address=email_address,
                login=login,
                password=await hash_password(password),
                phone_number=phone_number,
                about=about,
                date_and_time_registered=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)

            db.add(Chat(chat_kind=ChatKind.PROFILE, owner_user_id=user.id, date_and_time_created=datetime.datetime.now(datetime.timezone.utc)))
            await db.commit()
            return user

    async def create_friendship(self, first_user: User, second_user: User) -> Friendship:
        async with database.async_session_maker() as db:
            friendship = Friendship(
                user_id=min(first_user.id, second_user.id),
                friend_user_id=max(first_user.id, second_user.id),
                date_and_time_added=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(friendship)
            await db.commit()
            await db.refresh(friendship)
            return friendship

    async def create_friend_request(self, sender: User, receiver: User) -> FriendRequest:
        async with database.async_session_maker() as db:
            friend_request = FriendRequest(
                sender_user_id=sender.id,
                receiver_user_id=receiver.id,
                date_and_time_sent=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(friend_request)
            await db.commit()
            await db.refresh(friend_request)
            return friend_request

    async def create_chat(
        self,
        *,
        chat_kind: ChatKind,
        owner_user_id: int | None,
        name: str | None,
        members: list[tuple[User, ChatRole]],
    ) -> Chat:
        async with database.async_session_maker() as db:
            chat = Chat(
                chat_kind=chat_kind,
                owner_user_id=owner_user_id,
                name=name,
                date_and_time_created=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(chat)
            await db.flush()
            await db.refresh(chat)

            for user, role in members:
                db.add(
                    ChatMembership(
                        chat_id=chat.id,
                        chat_user_id=user.id,
                        chat_role=role,
                        date_and_time_added=datetime.datetime.now(datetime.timezone.utc),
                    )
                )

            await db.commit()
            return chat

    async def create_message(
        self,
        *,
        chat: Chat,
        sender: User,
        message_text: str,
        parent_message_id: int | None = None,
        reply_message_id: int | None = None,
    ) -> Message:
        async with database.async_session_maker() as db:
            message = Message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                date_and_time_sent=datetime.datetime.now(datetime.timezone.utc),
                date_and_time_edited=None,
                reply_message_id=reply_message_id,
                message_text=message_text,
                parent_message_id=parent_message_id,
                is_notification=False,
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)
            return message

    async def create_message_receipt(self, *, message: Message, receiver: User) -> MessageReceipt:
        async with database.async_session_maker() as db:
            receipt = MessageReceipt(
                message_id=message.id,
                receiver_user_id=receiver.id,
                date_and_time_received=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(receipt)
            await db.commit()
            await db.refresh(receipt)
            return receipt

    async def get_user_block(self, blocker_id: int, blocked_id: int) -> UserBlock | None:
        async with database.async_session_maker() as db:
            return (
                (
                    await db.execute(
                        sqlalchemy.select(UserBlock).where(
                            sqlalchemy.and_(UserBlock.user_id == blocker_id, UserBlock.blocked_user_id == blocked_id)
                        )
                    )
                )
                .scalars()
                .first()
            )

    async def scalar(self, statement: Any) -> Any:
        async with database.async_session_maker() as db:
            return (await db.execute(statement)).scalars().first()

    async def scalars(self, statement: Any) -> list[Any]:
        async with database.async_session_maker() as db:
            return list((await db.execute(statement)).scalars().all())

    async def count(self, model: Any) -> int:
        async with database.async_session_maker() as db:
            return int((await db.execute(sqlalchemy.select(sqlalchemy.func.count()).select_from(model))).scalar_one())

    async def object_exists_in_minio(self, bucket: minio_handler.MinioBucket, object_name: str) -> bool:
        client = await minio_handler.get_minio_client()
        try:
            client.client.stat_object(bucket.value, object_name)
            return True
        except Exception:
            return False

    async def get_minio_object_names(self, bucket: minio_handler.MinioBucket) -> list[str]:
        client = await minio_handler.get_minio_client()
        return [item.object_name for item in client.client.list_objects(bucket.value, recursive=True)]

    async def issue_session(self, user: User, user_agent: str = "pytest-client") -> str:
        redis_client = redis_handler.RedisClient(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB)
        try:
            return await redis_client.create_user_session(user.id, user_agent)
        finally:
            await redis_client.client.aclose()

    def authorize(self, client: TestClient, user: User, user_agent: str = "pytest-client") -> str:
        session_id = run_async(self.issue_session(user, user_agent))
        client.cookies.set("session_id", session_id)
        client.headers.update({"user-agent": user_agent})
        return session_id

    def seed_users(self) -> dict[str, User]:
        users = {
            "ivan": run_async(
                self.create_user(
                    username="иван_петров",
                    name="Иван",
                    surname="Петров",
                    second_name="Сергеевич",
                    email_address="ivan.petrov@example.com",
                    login="ivan.petrov",
                    password="секрет123",
                    about="Люблю велопоездки и короткие созвоны.",
                    phone_number="+79990000001",
                )
            ),
            "maria": run_async(
                self.create_user(
                    username="мария_соколова",
                    name="Мария",
                    surname="Соколова",
                    second_name="Игоревна",
                    email_address="maria.sokolova@example.com",
                    login="maria.sokolova",
                    password="секрет123",
                    about="Собираю идеи для книжного клуба.",
                    phone_number="+79990000002",
                )
            ),
            "oleg": run_async(
                self.create_user(
                    username="олег_смирнов",
                    name="Олег",
                    surname="Смирнов",
                    second_name="Андреевич",
                    email_address="oleg.smirnov@example.com",
                    login="oleg.smirnov",
                    password="секрет123",
                    about="Люблю походы и вечерние обсуждения.",
                    phone_number="+79990000003",
                )
            ),
            "anna": run_async(
                self.create_user(
                    username="анна_лебедева",
                    name="Анна",
                    surname="Лебедева",
                    second_name="Викторовна",
                    email_address="anna.lebedeva@example.com",
                    login="anna.lebedeva",
                    password="секрет123",
                    about="Пишу кратко и по делу.",
                    phone_number="+79990000004",
                )
            ),
        }
        return users


@pytest.fixture
def ctx(email_outbox: list[dict[str, str]]) -> IntegrationHelper:
    return IntegrationHelper(email_outbox)
