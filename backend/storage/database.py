import enum
import os
from datetime import datetime, date
import sqlalchemy.orm
import sqlalchemy.event
import sqlalchemy.dialects
import database_triggers

class Gender(enum.Enum):
    male = "Male"
    female = "Female"

class ChatKind(enum.Enum):
    private = "Private"
    group = "Group"
    community = "Community"
    discussion = "Discussion"
    wall = "Wall"

class ChatRole(enum.Enum):
    user = "User"
    admin = "Admin"
    owner = "Owner"


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True)
    username: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False)
    name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False)
    surname: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    second_name: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    date_of_birth: sqlalchemy.orm.Mapped[date | None] = sqlalchemy.orm.mapped_column(sqlalchemy.Date)
    gender: sqlalchemy.orm.Mapped[Gender | None] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(Gender))
    email_address: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(260), nullable=False)
    phone_number: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(50))
    about: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(5000))
    avatar_photo_path: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250))
    login: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100), nullable=False)
    password: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(255), nullable=False)
    date_and_time_registered: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('username', name="users_username_key"),
                      sqlalchemy.UniqueConstraint('email_address', name="users_email_address_key"),
                      sqlalchemy.UniqueConstraint('phone_number', name="users_phone_number_key"),
                      sqlalchemy.UniqueConstraint('login', name="users_login_key"),
                      sqlalchemy.Index('idx_users_username', 'UPPER(username)'),
                      sqlalchemy.Index('idx_users_name', 'UPPER(name)'),
                      sqlalchemy.Index('idx_users_surname', 'UPPER(surname)'),
                      sqlalchemy.Index('idx_users_second_name', 'UPPER(second_name)'),
                      sqlalchemy.Index('idx_users_name_surname_second_name', 'UPPER(name)', 'UPPER(surname)', 'UPPER(second_name)'),
                      sqlalchemy.Index('idx_users_login', 'login'),
                      sqlalchemy.Index('idx_users_email_address', 'email_address'),
                      sqlalchemy.Index('idx_users_phone_number', 'phone_number'))


class UserFriend(Base):
    __tablename__ = 'user_friends'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    friend_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_added: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (
        sqlalchemy.UniqueConstraint('user_id', 'friend_user_id', name='user_friends_user_id_friend_user_id_key'),
        sqlalchemy.CheckConstraint("user_id != friend_user_id"),
        sqlalchemy.Index('idx_user_friends_user_id', 'user_id'),
        sqlalchemy.Index('idx_user_friends_friend_user_id', 'friend_user_id'))


class UserFriendRequest(Base):
    __tablename__ = 'user_friend_requests'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    sender_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_sent: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('sender_user_id', 'receiver_user_id', name='user_friend_requests_sender_user_id_receiver_user_id_key'),
                      sqlalchemy.CheckConstraint("sender_user_id != receiver_user_id"),
                      sqlalchemy.Index('idx_user_friend_requests_sender_user_id', 'sender_user_id'),
                      sqlalchemy.Index('idx_user_friend_requests_receiver_user_id', 'receiver_user_id'))


class Chat(Base):
    __tablename__ = 'chats'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_kind: sqlalchemy.orm.Mapped[ChatKind] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(ChatKind), nullable=False)
    name: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(100))
    owner_user_id: sqlalchemy.orm.Mapped[int | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'))
    date_and_time_created: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    avatar_photo_path: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250))
    is_read_only: sqlalchemy.orm.Mapped[bool] = sqlalchemy.orm.mapped_column(sqlalchemy.BOOLEAN(), nullable = False)
    discussion_message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT(), sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'))
    __table_args__ = (sqlalchemy.UniqueConstraint("private_chat_key", name='private_chat_key_key'),
                      sqlalchemy.Index('idx_chats_name', 'UPPER(name)'),)


class ChatUser(Base):
    __tablename__ = 'chat_users'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    chat_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_added: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    chat_role: sqlalchemy.orm.Mapped[ChatRole] = sqlalchemy.orm.mapped_column(sqlalchemy.Enum(ChatRole), nullable=False)
    is_active: sqlalchemy.orm.Mapped[bool] = sqlalchemy.orm.mapped_column(sqlalchemy.BOOLEAN(), nullable = False)
    __table_args__ = (sqlalchemy.UniqueConstraint('chat_id', 'chat_user_id', name='chat_users_chat_id_chat_user_id_key'),)


class Message(Base):
    __tablename__ = 'messages'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    chat_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    sender_user_id: sqlalchemy.orm.Mapped[int | None] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='SET NULL'))
    date_and_time_sent: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    date_and_time_edited: sqlalchemy.orm.Mapped[datetime | None] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True))
    reply_message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='SET NULL'), nullable=False)
    message_text: sqlalchemy.orm.Mapped[str | None] = sqlalchemy.orm.mapped_column(sqlalchemy.TEXT)
    message_text_tsvector = sqlalchemy.orm.mapped_column(sqlalchemy.dialects.postgresql.TSVECTOR, sqlalchemy.Computed("TO_TSVECTOR('russian', message_text)", persisted=True))
    __table_args__ = (sqlalchemy.Index("idx_messages_chat_id", "chat_id"),
                      sqlalchemy.Index('idx_messages_chat_id_date_and_time_sent', 'chat_id', 'date_and_time_sent'),
                      sqlalchemy.Index('idx_messages_message_text_tsvector', 'message_text_tsvector', postgresql_using='gin'))


class FileAttachment(Base):
    __tablename__ = 'file_attachments'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    attachment_file_path: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(sqlalchemy.VARCHAR(250), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('message_id', 'attachment_file_path', name='file_attachments_message_id_attachments_file_path_key'),)


class ReceivedMessage(Base):
    __tablename__ = 'received_messages'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    message_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    receiver_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_received: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint('message_id', 'receiver_user_id', name='received_messages_message_id_receiver_user_id_key'),)


class BlockedUser(Base):
    __tablename__ = 'blocked_users'
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, primary_key=True, autoincrement=True)
    user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    blocked_user_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(sqlalchemy.BIGINT, sqlalchemy.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date_and_time_blocked: sqlalchemy.orm.Mapped[datetime] = sqlalchemy.orm.mapped_column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (sqlalchemy.UniqueConstraint("user_id", "blocked_user_id", name="blocked_users_user_id_blocked_user_id_key"),
                    sqlalchemy.Index('idx_blocked_users_user_id', 'user_id'),
                    sqlalchemy.Index('idx_blocked_users_blocked_user_id', 'blocked_user_id'),
                    sqlalchemy.Index('idx_blocked_users_user_id_blocked_user_id', 'user_id', 'blocked_user_id'),)


sqlalchemy.event.listen(ChatUser, "after_insert", database_triggers.chat_user_after_insert)
sqlalchemy.event.listen(ChatUser, "after_delete", database_triggers.chat_user_after_delete)
sqlalchemy.event.listen(ChatUser, "after_update", database_triggers.chat_user_after_update)
sqlalchemy.event.listen(Chat, "after_update", database_triggers.chat_after_update)
sqlalchemy.event.listen(Message, "after_insert", database_triggers.message_after_insert)
sqlalchemy.event.listen(Message, "after_update", database_triggers.message_after_update)
sqlalchemy.event.listen(Message, "after_delete", database_triggers.message_after_delete)
sqlalchemy.event.listen(ReceivedMessage, "after_insert", database_triggers.message_read_mark_after_insert)
sqlalchemy.event.listen(ReceivedMessage, "after_insert", database_triggers.message_attachment_after_insert)
sqlalchemy.event.listen(ReceivedMessage, "after_delete", database_triggers.message_attachment_after_delete)

database_url: str = "postgresql://" + os.getenv("POSTGRES_USER") + ":" + os.getenv("POSTGRES_PASSWORD") + "@" + os.getenv("POSTGRES_HOST") + ":" + os.getenv("POSTGRES_PORT") + "/" + os.getenv("POSTGRES_DB")
db_engine: sqlalchemy.Engine = sqlalchemy.create_engine(database_url)
Base.metadata.create_all(db_engine)
session_maker: sqlalchemy.orm.session.sessionmaker = sqlalchemy.orm.sessionmaker(bind=db_engine)


async def get_db():
    db = session_maker()
    try:
        yield db
    finally:
        db.close()