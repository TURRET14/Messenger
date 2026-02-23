import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql

from backend.storage import *

async def get_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> ChatUser:

    membership: ChatUser = db.execute(sqlalchemy.select(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id,
    ChatUser.chat_user_id == selected_user.id, ChatUser.is_active == True))).scalars().first()

    return membership


async def get_users_friendship(
    first_user: User,
    second_user: User,
    db: sqlalchemy.orm.session.Session) -> UserFriend:

    friendship: UserFriend = db.execute(sqlalchemy.select(UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == first_user.id,
    UserFriend.friend_user_id == second_user.id),
    sqlalchemy.and_(UserFriend.user_id == second_user.id,
    UserFriend.friend_user_id == first_user.id)))).scalars().first()

    return friendship


async def is_chat_user_owner_or_admin(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> bool:

    if (not is_chat_user_owner(selected_chat, selected_user) and db.execute(sqlalchemy.select(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id,
    ChatUser.chat_user_id == selected_user.id)))
    .scalars().first().chat_role == ChatRole.admin):
        return False
    else:
        return True


async def is_chat_user_owner(
    selected_chat: Chat,
    selected_user: User) -> bool:

    if selected_chat.owner_user_id != selected_user.id:
        return False
    else:
        return True

async def get_users_private_chat(
    first_user: User,
    second_user: User,
    db: sqlalchemy.orm.session.Session) -> Chat:

    first_subquery: sqlalchemy.sql.Subquery = (sqlalchemy.select(ChatUser.chat_id.label("left_chat_id")).select_from(ChatUser)
    .where(ChatUser.chat_user_id == first_user.id).join(Chat, Chat.id == ChatUser.chat_id)
    .where(Chat.chat_kind == ChatKind.private).subquery())
    second_subquery: sqlalchemy.sql.Subquery = (sqlalchemy.select(ChatUser.chat_id.label("right_chat_id")).select_from(ChatUser)
    .where(ChatUser.chat_user_id == second_user.id).join(Chat, Chat.id == ChatUser.chat_id)
    .where(Chat.chat_kind == ChatKind.private).subquery())

    chat: Chat = db.execute(sqlalchemy.select(Chat).select_from(first_subquery).join(second_subquery,second_subquery.c.right_chat_id == first_subquery.c.left_chat_id).join(Chat, Chat.id == first_subquery.c.left_chat_id)).scalars().first()

    return chat


async def is_private_chat_active(
    private_chat: Chat,
    db: sqlalchemy.orm.session.Session) -> bool:

    if not private_chat or private_chat.chat_kind != ChatKind.private:
        return False
    else:
        if db.execute(sqlalchemy.select(sqlalchemy.func.count(Chat.id)).select_from(Chat).where(Chat.id == private_chat.id).join(ChatUser, ChatUser.chat_id == Chat.id).where(ChatUser.is_active == True)).scalar() != 2:
            return False
        else:
            return True


async def get_user_chat_membership(
    private_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> ChatUser:

    return db.execute(sqlalchemy.select(ChatUser).where(sqlalchemy.and_(ChatUser.chat_user_id == selected_user.id, ChatUser.chat_id == private_chat.id, ChatUser.is_active == True))).scalars().first()