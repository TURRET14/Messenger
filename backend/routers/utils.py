import fastapi
import sqlalchemy.orm

from backend.storage import *
from backend.return_details import *

async def get_chat_user_membership(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> ChatUser:

    membership: ChatUser = db.execute(sqlalchemy.select(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id,
    ChatUser.chat_user_id == selected_user.id))).scalars().first()

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