import enum
import os
import datetime
import sqlalchemy.orm
import sqlalchemy.event
import sqlalchemy.dialects
import database_triggers
import sqlalchemy.ext.asyncio
import asyncio

class Gender(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class ChatKind(enum.Enum):
    PRIVATE = "PRIVATE"
    GROUP = "GROUP"
    CHANNEL = "CHANNEL"
    PROFILE = "PROFILE"

class ChatRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    OWNER = "OWNER"


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True)
    username: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False, unique=True)
    name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False)
    surname: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    second_name: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    date_of_birth: sqlalchemy.orm.Mapped[datetime.date | None] = sqlalchemy.orm.mapped_column(sqlalchemy.Date)
    gender: sqlalchemy.orm.Mapped[Gender | None] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(Gender, name='genders_enum'))
    email_address: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(260), nullable=False, unique=True)
    phone_number: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(50), unique=True)
    about: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(5000))
    avatar_photo_path: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250))
    login: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False, unique=True)
    password: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(255), nullable=False)
    date_and_time_registered: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.Index('idx_users_username', sqlalchemy.func.upper(username)),
                    sqlalchemy.Index('idx_users_name', sqlalchemy.func.upper(name)),
                    sqlalchemy.Index('idx_users_surname', sqlalchemy.func.upper(surname)),
                    sqlalchemy.Index('idx_users_second_name', sqlalchemy.func.upper(second_name)),
                    sqlalchemy.Index('idx_users_name_surname_second_name', sqlalchemy.func.upper(name), sqlalchemy.func.upper(surname), sqlalchemy.func.upper(second_name)),
                    sqlalchemy.Index('idx_users_login', login),
                    sqlalchemy.Index('idx_users_email_address', email_address),
                    sqlalchemy.Index('idx_users_phone_number', phone_number))


class Friendship(Base):
    __tablename__ = 'friendships'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    friend_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_added: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint(user_id, friend_user_id),
                    sqlalchemy.CheckConstraint(user_id < friend_user_id),
                    sqlalchemy.Index('idx_friends_user_id', user_id),
                    sqlalchemy.Index('idx_friends_friend_user_id', friend_user_id),
                    sqlalchemy.Index('idx_friends_user_id_friend_user_id', user_id, friend_user_id))


class FriendRequest(Base):
    __tablename__ = 'friend_requests'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    sender_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_sent: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.CheckConstraint(sender_user_id != receiver_user_id),
                    sqlalchemy.Index('uq_friend_requests_sender_user_id_receiver_user_id', sqlalchemy.func.least(sender_user_id, receiver_user_id), sqlalchemy.func.greatest(sender_user_id, receiver_user_id), unique=True),
                    sqlalchemy.Index('idx_friend_requests_sender_user_id', sender_user_id),
                    sqlalchemy.Index('idx_friend_requests_receiver_user_id', receiver_user_id),
                    sqlalchemy.Index('idx_friend_requests_sender_user_id_receiver_user_id', sender_user_id, receiver_user_id))


class Chat(Base):
    __tablename__ = 'chats'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_kind: sqlalchemy.orm.Mapped[ChatKind] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(ChatKind, name='chat_types_enum'), nullable=False)
    name: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    owner_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'))
    date_and_time_created: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    avatar_photo_path: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250))
    __table_args__ = (sqlalchemy.Index('idx_chats_name', sqlalchemy.func.upper(name)),
                    sqlalchemy.Index('idx_chats_chat_kind', chat_kind))


class ChatMembership(Base):
    __tablename__ = 'chat_memberships'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    chat_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_added: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    chat_role: sqlalchemy.orm.Mapped[ChatRole] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(ChatRole, name='chat_roles_enum'), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint(chat_id, chat_user_id),
                    sqlalchemy.Index('idx_chat_members_chat_id', chat_id),
                    sqlalchemy.Index('idx_chat_members_chat_user_id', chat_user_id),
                    sqlalchemy.Index('idx_chat_members_chat_id_chat_user_id', chat_id, chat_user_id),
                    sqlalchemy.Index('idx_chat_members_chat_id_date_and_time_added_chat_role', chat_id, date_and_time_added, chat_role))


class Message(Base):
    __tablename__ = 'messages'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    sender_user_id: sqlalchemy.orm.Mapped[int | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='SET NULL'))
    date_and_time_sent: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    date_and_time_edited: sqlalchemy.orm.Mapped[datetime.datetime | None] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True))
    reply_message_id: sqlalchemy.orm.Mapped[int | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='SET NULL'))
    message_text: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.TEXT)
    message_text_tsvector: sqlalchemy.orm.Mapped[sqlalchemy.dialects.postgresql.TSVECTOR | None] = sqlalchemy.orm.mapped_column(sqlalchemy.dialects.postgresql.TSVECTOR, sqlalchemy.Computed("TO_TSVECTOR('russian', message_text)", persisted=True))
    parent_message_id: sqlalchemy.orm.Mapped[int | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'))
    is_notification: sqlalchemy.orm.Mapped[bool | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BOOLEAN)
    __table_args__ = (sqlalchemy.Index('idx_messages_chat_id', chat_id),
                    sqlalchemy.Index('idx_messages_sender_user_id', sender_user_id),
                    sqlalchemy.Index('idx_messages_chat_id_sender_user_id', chat_id, sender_user_id),
                    sqlalchemy.Index('idx_messages_chat_id_date_and_time_sent', chat_id, date_and_time_sent),
                    sqlalchemy.Index('idx_messages_message_text_tsvector', message_text_tsvector, postgresql_using='gin'))


class MessageAttachment(Base):
    __tablename__ = 'message_attachments'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    attachment_file_path: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250), nullable=False, unique=True)
    __table_args__ = (sqlalchemy.Index('idx_message_attachments_message_id', message_id),)


class MessageReceipt(Base):
    __tablename__ = 'message_receipts'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    receiver_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_received: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('message_id', receiver_user_id),
                    sqlalchemy.Index('idx_message_receipts_message_id', message_id),
                    sqlalchemy.Index('idx_message_receipts_receiver_user_id', receiver_user_id),
                    sqlalchemy.Index('idx_message_receipts_message_id_receiver_user_id', message_id, receiver_user_id))


class UserBlock(Base):
    __tablename__ = 'user_blocks'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    blocked_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_blocked: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('user_id', blocked_user_id),
                    sqlalchemy.Index('idx_user_blocks_user_id', user_id),
                    sqlalchemy.Index('idx_user_blocks_blocked_user_id', blocked_user_id),
                    sqlalchemy.Index('idx_user_blocks_user_id_blocked_user_id', user_id, blocked_user_id))


sqlalchemy.event.listen(ChatMembership, "after_insert", database_triggers.chat_user_after_insert)
sqlalchemy.event.listen(ChatMembership, "after_delete", database_triggers.chat_user_after_delete)
sqlalchemy.event.listen(ChatMembership, "after_update", database_triggers.chat_user_after_update)
sqlalchemy.event.listen(Chat, "after_update", database_triggers.chat_after_update)
sqlalchemy.event.listen(Message, "after_insert", database_triggers.message_after_insert)
sqlalchemy.event.listen(Message, "after_update", database_triggers.message_after_update)
sqlalchemy.event.listen(Message, "after_delete", database_triggers.message_after_delete)
sqlalchemy.event.listen(MessageReceipt, "after_insert", database_triggers.message_read_mark_after_insert)
sqlalchemy.event.listen(MessageAttachment, "after_insert", database_triggers.message_attachment_after_insert)
sqlalchemy.event.listen(MessageAttachment, "after_delete", database_triggers.message_attachment_after_delete)

database_url: str = "postgresql+psycopg://" + str(os.getenv("POSTGRES_USER")) + ":" + str(os.getenv("POSTGRES_PASSWORD")) + "@" + str(os.getenv("POSTGRES_HOST")) + ":" + str(os.getenv("POSTGRES_PORT")) + "/" + str(os.getenv("POSTGRES_DB"))
db_engine: sqlalchemy.ext.asyncio.AsyncEngine = sqlalchemy.ext.asyncio.create_async_engine(database_url)
session_maker: sqlalchemy.ext.asyncio.async_sessionmaker = sqlalchemy.ext.asyncio.async_sessionmaker(bind=db_engine)

async def init_db():
    async with db_engine.connect() as conn:
        await conn.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection))

asyncio.create_task(init_db())

async def get_db():
    db = session_maker()
    try:
        yield db
    finally:
        await db.close()