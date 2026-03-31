import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from backend.storage import *


async def is_username_already_taken(
    username: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if (await db.execute(sqlalchemy.select(User).where(User.username == username))).scalars().first():
        return True
    else:
        return False


async def is_login_already_taken(
    login: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if (await db.execute(sqlalchemy.select(User).where(User.login == login))).scalars().first():
        return True
    else:
        return False


async def is_email_already_taken(
    email_address: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if (await db.execute(sqlalchemy.select(User).where(User.email_address == email_address))).scalars().first():
        return True
    else:
        return False


async def is_phone_number_already_taken(
    phone_number: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if (await db.execute(sqlalchemy.select(User).where(User.phone_number == phone_number))).scalars().first():
        return True
    else:
        return False


async def get_friend_request(
    sender_user_id: int,
    receiver_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> FriendRequest:

    friend_request: FriendRequest = ((await db.execute(sqlalchemy.select(FriendRequest)
    .where(sqlalchemy.and_(FriendRequest.sender_user_id == sender_user_id,
    FriendRequest.receiver_user_id == receiver_user_id)))).scalars().first())

    return friend_request


async def are_users_already_friends(
    first_user_id: int,
    second_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> bool:

    if (await (db.execute(sqlalchemy.select(Friendship)
    .where((sqlalchemy.and_(Friendship.user_id == min(first_user_id, second_user_id), Friendship.friend_user_id == max(first_user_id, second_user_id))))))).scalars().first():
        return True
    else:
        return False


async def get_user_block(
    selected_user_id: int,
    blocked_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> UserBlock:

    return ((await db.execute(sqlalchemy.select(UserBlock)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserBlock.user_id == selected_user_id, UserBlock.blocked_user_id == blocked_user_id)))))
    .scalars().first())


async def get_friendship(
    first_user_id: int,
    second_user_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> Friendship:

    friendship: Friendship = ((await db.execute(sqlalchemy.select(Friendship)
                                                .where(sqlalchemy.and_(Friendship.user_id == min(first_user_id, second_user_id), Friendship.friend_user_id == max(first_user_id, second_user_id)))))
                              .scalars().first())

    return friendship