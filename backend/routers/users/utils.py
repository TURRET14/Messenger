import sqlalchemy.orm
from backend.storage import *


async def is_username_already_taken(
    username: str,
    db: sqlalchemy.orm.session.Session) -> bool:

    if db.execute(sqlalchemy.select(User).where(User.username == username)).scalars().first():
        return True
    else:
        return False


async def is_login_already_taken(
    login: str,
    db: sqlalchemy.orm.session.Session) -> bool:

    if db.execute(sqlalchemy.select(User).where(User.login == login)).scalars().first():
        return True
    else:
        return False


async def is_email_already_taken(
    email_address: str,
    db: sqlalchemy.orm.session.Session) -> bool:

    if db.execute(sqlalchemy.select(User).where(User.email_address == email_address)).scalars().first():
        return True
    else:
        return False


async def is_phone_number_already_taken(
    phone_number: str,
    db: sqlalchemy.orm.session.Session) -> bool:

    if db.execute(sqlalchemy.select(User).where(User.phone_number == phone_number)).scalars().first():
        return True
    else:
        return False

async def does_friend_request_already_exist(
    first_user_id: int,
    second_user_id: int,
    db: sqlalchemy.orm.session.Session) -> bool:

    if (db.execute(sqlalchemy.select(UserFriendRequest).where(sqlalchemy.and_(UserFriendRequest.sender_user_id == first_user_id, UserFriendRequest.receiver_user_id == second_user_id))).scalars().first() or
    db.execute(sqlalchemy.select(UserFriendRequest).where(sqlalchemy.and_(UserFriendRequest.sender_user_id == second_user_id, UserFriendRequest.receiver_user_id == first_user_id))).scalars().first()):
        return True
    else:
        return False


async def are_users_already_friends(
    first_user_id: int,
    second_user_id: int,
    db: sqlalchemy.orm.session.Session) -> bool:

    if (db.execute(sqlalchemy.select(UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == first_user_id,
    UserFriend.friend_user_id == second_user_id), sqlalchemy.and_(UserFriend.user_id == second_user_id,
    UserFriend.friend_user_id == first_user_id)))).scalars().first()):
        return True
    else:
        return False


async def get_user_block(
    selected_user: User,
    blocked_user: User,
    db: sqlalchemy.orm.session.Session) -> BlockedUser:

    return db.execute(sqlalchemy.select(BlockedUser).where(sqlalchemy.or_(sqlalchemy.and_(BlockedUser.user_id == selected_user.id, BlockedUser.blocked_user_id == blocked_user.id)))).scalar()