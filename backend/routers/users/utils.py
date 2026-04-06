import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from sqlalchemy import Sequence

from backend.storage import *


async def get_friend_request(
    sender_user: User,
    receiver_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> FriendRequest | None:

    friend_request: FriendRequest | None = ((await db.execute(
    sqlalchemy.select(FriendRequest)
    .where(sqlalchemy.and_(FriendRequest.sender_user_id == sender_user.id, FriendRequest.receiver_user_id == receiver_user.id))))
    .scalars().first())

    return friend_request


async def get_user_block(
    selected_user: User,
    blocked_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> UserBlock | None:

    user_block: UserBlock | None = ((await db.execute(
    sqlalchemy.select(UserBlock)
    .where(sqlalchemy.and_(UserBlock.user_id == selected_user.id, UserBlock.blocked_user_id == blocked_user.id))))
    .scalars().first())

    return user_block


async def get_friendship(
    selected_user: User,
    friend_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Friendship | None:

    friendship: Friendship | None = ((await (db.execute(
    sqlalchemy.select(Friendship)
    .where((sqlalchemy.and_(Friendship.user_id == min(selected_user.id, friend_user.id),
    Friendship.friend_user_id == max(selected_user.id, friend_user.id)))))))
    .scalars().first())

    return friendship


async def get_all_user_dependent_chats(
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Sequence[Chat]:

    chats_list: Sequence[Chat] = ((await db.execute(
    sqlalchemy.select(Chat)
    .select_from(ChatMembership)
    .where(ChatMembership.chat_user_id == selected_user.id)
    .join(Chat, Chat.id == ChatMembership.chat_id)
    .where(sqlalchemy.or_(Chat.owner_user_id == selected_user.id, Chat.chat_kind == ChatKind.PRIVATE))))
    .scalars().all())

    return chats_list
