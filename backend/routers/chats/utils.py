import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql
import sqlalchemy.ext.asyncio

from backend.storage import *

async def get_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> ChatMembership | None:

    membership: ChatMembership | None = (await db.execute(sqlalchemy.select(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat.id,
    ChatMembership.chat_user_id == selected_user.id)))).scalars().first()

    return membership

async def get_users_private_chat(
    first_user: User,
    second_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Chat | None:

    first_subquery: sqlalchemy.sql.Subquery = (sqlalchemy.select(ChatMembership.chat_id.label("left_chat_id")).select_from(ChatMembership)
    .where(ChatMembership.chat_user_id == first_user.id).join(Chat, Chat.id == ChatMembership.chat_id)
    .where(Chat.chat_kind == ChatKind.PRIVATE).subquery())
    second_subquery: sqlalchemy.sql.Subquery = (sqlalchemy.select(ChatMembership.chat_id.label("right_chat_id")).select_from(ChatMembership)
    .where(ChatMembership.chat_user_id == second_user.id).join(Chat, Chat.id == ChatMembership.chat_id)
    .where(Chat.chat_kind == ChatKind.PRIVATE).subquery())

    chat: Chat | None = (await db.execute(sqlalchemy.select(Chat).select_from(first_subquery).join(second_subquery,second_subquery.c.right_chat_id == first_subquery.c.left_chat_id).join(Chat, Chat.id == first_subquery.c.left_chat_id))).scalars().first()

    return chat


async def get_chat_name(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> str:

    if selected_chat.name:
        return selected_chat.name
    else:
        chat_name: str = str(((await db.execute(
        sqlalchemy.select(sqlalchemy.func.string_agg(User.name + " " + User.surname + " " + User.second_name, ", "))
        .select_from(ChatMembership)
        .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat.id, ChatMembership.chat_user_id != selected_user.id))
        .join(User, User.id == ChatMembership.chat_user_id)))
        .scalars().first()))

        return chat_name

async def get_other_chat_user(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> User | None:

    other_user: User | None = ((await db.execute(
    sqlalchemy.select(User)
    .select_from(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat.id, ChatMembership.chat_user_id != selected_user.id))
    .join(User, User.id == ChatMembership.chat_user_id)))
    .scalars().first())

    return other_user