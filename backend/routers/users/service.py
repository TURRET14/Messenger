import datetime
import uuid
from typing import Sequence

import fastapi
import fastapi.encoders
import minio.datatypes
import sqlalchemy
import sqlalchemy.orm
import pathlib
import io
import redis.asyncio
import secrets
import asyncio

import backend.routers.dependencies
import backend.routers.password_hashing
import backend.routers.parameters
import backend.routers.return_details
from backend.storage import *
import backend.routers.chats.utils
from models import (
    RegisterModel,
    LoginModel,
    SessionModel,
    UserUpdateModel,
    UserUpdateLoginModel,
    UserUpdatePasswordModel,
    UserResponseModel,
    LoginResponseModel)
import utils

async def create_user(
    data: RegisterModel,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if await utils.is_username_already_taken(data.username, db):
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.USERNAME_ALREADY_TAKEN_ERROR)

    if await utils.is_email_already_taken(data.email_address, db):
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.EMAIL_ALREADY_TAKEN_ERROR)

    if await utils.is_login_already_taken(data.login, db):
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.LOGIN_ALREADY_TAKEN_ERROR)

    new_user: User = User(
    username = data.username,
    name = data.name,
    email_address = data.email_address,
    login = data.login,
    password = backend.routers.password_hashing.hash_password(data.password),
    surname = data.surname,
    second_name = data.second_name,
    date_and_time_registered = datetime.datetime.now(datetime.timezone.utc))

    db.add(new_user)

    user_wall: Chat = Chat(owner_user_id = new_user.id, chat_kind = ChatKind.wall)
    db.add(user_wall)

    db.commit()
    db.refresh(new_user)

    return fastapi.responses.JSONResponse({"id": new_user.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def login(
    data: LoginModel,
    response: fastapi.responses.Response,
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.asyncio.Redis) -> fastapi.responses.JSONResponse:

    selected_user: User = (db.execute(
    sqlalchemy.select(User)
    .where(User.login == data.login))
    .scalars().first())

    if not selected_user:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INCORRECT_LOGIN_ERROR)

    if backend.routers.password_hashing.verify_password(selected_user.password, data.password):
        # Добавление сессии в Redis (Новая запись в словарь сессий + Новое значение во множестве сессий пользователя)
        session_id = secrets.token_urlsafe(64)
        expiration_date: int = int(datetime.datetime.now().timestamp()) + int(datetime.timedelta(seconds = backend.routers.parameters.redis_session_expiration_time_seconds).total_seconds())

        coroutines: list = list()
        coroutines.append(redis_client.sadd(f"user:{selected_user.id}:sessions", session_id))
        coroutines.append(redis_client.hset(f"session:{session_id}:data",
        mapping = {"user_id": selected_user.id, "expiration_date": expiration_date}))
        coroutines.append(redis_client.expireat(f"user:{selected_user.id}:sessions", expiration_date))
        coroutines.append(redis_client.expireat(f"session:{session_id}:data", expiration_date))

        await asyncio.gather(*coroutines)

        response.set_cookie("session_id", value = session_id, max_age = backend.routers.parameters.redis_session_expiration_time_seconds, httponly = True, secure = True, samesite ="strict")

        return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INCORRECT_PASSWORD_ERROR)


async def delete_session(
    data: SessionModel,
    selected_user: User,
    redis_client: redis.asyncio.Redis) -> fastapi.responses.JSONResponse:

    # Удаление сессии из Redis (Удаление сессии из словаря сессий + Удаление значения сессии из множества сессий пользователя)
    # Сначала проверяется, принадлежит ли сессия пользователю
    session: dict[str, str] = await redis_client.hgetall(f"session:{data.session_id}:data")

    if not session:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    if int(session["user_id"]) != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INVALID_SESSION_ID_ERROR)

    coroutines: list = list()
    coroutines.append(redis_client.srem(f"user:{selected_user.id}:sessions", data.session_id))
    coroutines.append(redis_client.delete(f"session:{data.session_id}:data"))

    await asyncio.gather(*coroutines)

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_all_sessions(
    selected_user: User,
    redis_client: redis.asyncio.Redis) -> fastapi.responses.JSONResponse:

    # Удаление всех сессий пользователя из Redis (Удаление всех сессий пользователя из словаря сессий + Удаление множества сессий пользователя)
    session_list: set = await redis_client.smembers(f"user:{selected_user.id}:sessions")

    coroutines: list = list()
    for session_id in session_list:
        coroutines.append(redis_client.delete(f"session:{session_id}:data"))

    await asyncio.gather(*coroutines)
    await redis_client.delete(f"user:{selected_user.id}:sessions")

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def get_user(
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    selected_user: UserResponseModel = UserResponseModel(
        id =  selected_user.id,
        username = selected_user.username,
        name = selected_user.name,
        surname = selected_user.surname,
        second_name = selected_user.second_name,
        date_of_birth = selected_user.date_of_birth,
        gender = selected_user.gender,
        email_address = selected_user.email_address,
        phone_number = selected_user.phone_number,
        about = selected_user.about,
        date_and_time_registered = selected_user.date_and_time_registered
    )

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_user), status_code = fastapi.status.HTTP_200_OK)


async def get_user_login(
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    user_login: LoginResponseModel = LoginResponseModel(login = selected_user.login)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_login), status_code = fastapi.status.HTTP_200_OK)


async def update_user(
    data: UserUpdateModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if data.username != selected_user.username and await utils.is_username_already_taken(data.username, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.USERNAME_ALREADY_TAKEN_ERROR)

    if data.email_address != selected_user.email_address and await utils.is_email_already_taken(data.email_address, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.EMAIL_ALREADY_TAKEN_ERROR)

    if data.phone_number != selected_user.phone_number and await utils.is_phone_number_already_taken(data.phone_number, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.PHONE_NUMBER_ALREADY_TAKEN_ERROR)

    selected_user.username = data.username
    selected_user.name = data.name
    selected_user.surname = data.surname
    selected_user.second_name = data.second_name
    selected_user.date_of_birth = data.date_of_birth
    selected_user.gender = data.gender
    selected_user.email_address = data.email_address
    selected_user.phone_number = data.phone_number
    selected_user.about = data.about
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def update_user_login(
    data: UserUpdateLoginModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if data.login != selected_user.login and await utils.is_login_already_taken(data.login, db):
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.LOGIN_ALREADY_TAKEN_ERROR)

    selected_user.login = data.login
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def update_user_password(
    data: UserUpdatePasswordModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if backend.routers.password_hashing.verify_password(selected_user.password, data.old_password):
        selected_user.password = backend.routers.password_hashing.hash_password(data.new_password)
        db.commit()
        return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_PASSWORD_ERROR")

async def get_user_avatar(
    selected_user: User,
    minio_client: minio.Minio) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    if not selected_user.avatar_photo_path:
        return fastapi.responses.FileResponse(backend.routers.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)

    file = minio_client.get_object("users:avatars", selected_user.avatar_photo_path)
    file_stat = minio_client.stat_object("users:avatars", selected_user.avatar_photo_path)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def update_user_avatar(
    selected_user: User,
    file: fastapi.UploadFile,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if file.content_type not in backend.routers.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_TYPE_NOT_ALLOWED_ERROR)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.routers.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_TYPE_NOT_ALLOWED_ERROR)

    #MinIO - Загрузка аватара
    minio_file_name: str = f"users/{selected_user.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()

    if len(file_content) > backend.routers.parameters.max_avatar_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_SIZE_TOO_LARGE_ERROR)

    minio_client.put_object("users:avatars", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)

    # MinIO - Удаление старого аватара
    if selected_user.avatar_photo_path:
        minio_client.remove_object("users:avatars", selected_user.avatar_photo_path)

    selected_user.avatar_photo_path = minio_file_name
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code=fastapi.status.HTTP_200_OK)


async def delete_user(
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_user.avatar_photo_path:
        minio_client.remove_object("users:avatars", selected_user.avatar_photo_path)

    user_group_chats_and_communities: Sequence[Chat] = db.execute(sqlalchemy.select(Chat).where(sqlalchemy.and_(Chat.owner_user_id == selected_user.id, Chat.chat_kind.in_([ChatKind.group, ChatKind.community])))).scalars().all()

    for chat in user_group_chats_and_communities:
        db.delete(chat)

    db.execute(sqlalchemy.delete(Chat).where(Chat.id.in_(sqlalchemy.select(Chat.id).select_from(ChatUser).where(ChatUser.chat_user_id == selected_user.id).join(Chat, Chat.id == ChatUser.chat_id).where(Chat.chat_kind == ChatKind.private))))

    db.execute(sqlalchemy.delete(Chat).where(sqlalchemy.and_(Chat.owner_user_id == selected_user.id, Chat.chat_kind == ChatKind.wall)))

    db.delete(selected_user)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def get_users(
    offset_multiplier: int,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    users_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)


async def search_users_by_username(
    offset_multiplier: int,
    username: str,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    users_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .where(User.username.like(f"%{username}"))
    .order_by(User.id).offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def search_users_by_names(
    offset_multiplier: int,
    name: str | None,
    surname: str | None,
    second_name: str | None,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if name is None and surname is None and second_name is None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    select_request = sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)

    if name is not None:
        select_request = select_request.where(User.name.like(f"%{name}"))
    if surname is not None:
        select_request = select_request.where(User.surname.like(f"%{surname}"))
    if second_name is not None:
        select_request = select_request.where(User.second_name.like(f"%{second_name}"))

    users_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    select_request.order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def get_friends(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friends_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.user_id == selected_user.id)
    .join(User, User.id == UserFriend.friend_user_id)
    .union(
    sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.friend_user_id == selected_user.id)
    .join(User, User.id == UserFriend.user_id))
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_username(
    offset_multiplier: int,
    username: str,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friends_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.user_id == selected_user.id)
    .join(User, User.id == UserFriend.friend_user_id)
    .where(User.username.like(f"%{username}"))
    .union(
    sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.friend_user_id == selected_user.id)
    .join(User, User.id == UserFriend.user_id)
    .where(User.username.like(f"%{username}")))
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_names(
    offset_multiplier: int,
    name: str | None,
    surname: str | None,
    second_name: str | None,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if name is None and surname is None and second_name is None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not name:
        name = str()
    if not surname:
        surname = str()
    if not second_name:
        second_name = str()

    friends_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.user_id == selected_user.id)
    .join(User, User.id == UserFriend.friend_user_id)
    .where(sqlalchemy.and_(
    User.name.like(f"%{name}"),
    User.surname.like(f"%{surname}"),
    User.second_name.like(f"%{second_name}")))
    .union(
    sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(UserFriend)
    .where(UserFriend.friend_user_id == selected_user.id)
    .join(User, User.id == UserFriend.user_id)
    .where(sqlalchemy.and_(
    User.name.like(f"%{name}"),
    User.surname.like(f"%{surname}"),
    User.second_name.like(f"%{second_name}"))))
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_sent_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friend_requests_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    sqlalchemy.select(
    UserFriendRequest.id.label("friend_request_id"),
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    UserFriendRequest.date_and_time_sent)
    .select_from(UserFriendRequest)
    .where(UserFriendRequest.sender_user_id == selected_user.id)
    .join(User, User.id == UserFriendRequest.receiver_user_id)
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_received_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friend_requests_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    sqlalchemy.select(
    UserFriendRequest.id.label("friend_request_id"),
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    UserFriendRequest.date_and_time_sent)
    .select_from(UserFriendRequest)
    .where(UserFriendRequest.receiver_user_id == selected_user.id)
    .join(User, User.id == UserFriendRequest.sender_user_id)
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def send_friend_request(
    receiver: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if receiver.id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if utils.does_friend_request_already_exist(receiver.id, selected_user.id, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.CONFLICT_ERROR)

    if utils.are_users_already_friends(receiver.id, selected_user.id, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.CONFLICT_ERROR)

    if utils.get_user_block(selected_user, receiver, db) or utils.get_user_block(receiver, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    friend_request = UserFriendRequest(
    sender_user_id = selected_user.id,
    receiver_user_id = receiver.id,
    date_and_time_sent = datetime.datetime.now(datetime.timezone.utc))

    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)

    return fastapi.responses.JSONResponse({"id": friend_request.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def accept_friend_request(
    friend_request_id: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friend_request: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest)
    .where(UserFriendRequest.id == friend_request_id)).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    if friend_request.receiver_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.UNAUTHORIZED_ERROR)

    sender_user: User = db.execute(sqlalchemy.select(User).where(User.id == friend_request.sender_user_id)).scalars().first()

    if utils.get_user_block(selected_user, sender_user, db) or utils.get_user_block(sender_user, selected_user, db):
        db.delete(friend_request)
        db.commit()
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    friendship: UserFriend = UserFriend(
    user_id = friend_request.sender_user_id,
    friend_user_id = selected_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    db.delete(friend_request)
    db.add(friendship)
    db.commit()
    db.refresh(friendship)

    return fastapi.responses.JSONResponse({"id": friendship.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def decline_received_friend_request(
    friend_request_id: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friend_request: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest)
    .where(UserFriendRequest.id == friend_request_id)).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    if friend_request.receiver_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.UNAUTHORIZED_ERROR)

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_sent_friend_request(
    friend_request_id: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.USER_NOT_FOUND_ERROR)

    friend_request: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest)
    .where(UserFriendRequest.id == friend_request_id)).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    if friend_request.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.UNAUTHORIZED_ERROR)

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_friend(
    friend: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friendship: UserFriend = (db.execute(sqlalchemy.select(UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == selected_user.id, UserFriend.friend_user_id == friend.id),
    sqlalchemy.and_(UserFriend.user_id == friend.id, UserFriend.friend_user_id == selected_user.id))))
    .scalars().first())

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    db.delete(friendship)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def add_blocked_user(
    blocked_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if utils.get_user_block(selected_user, blocked_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.CONFLICT_ERROR)

    new_block: BlockedUser = BlockedUser(user_id = selected_user.id, blocked_user_id = blocked_user.id, date_and_time_blocked = datetime.datetime.now(datetime.timezone.utc))

    friendship: UserFriend = db.execute(sqlalchemy.select(UserFriend).where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == selected_user.id, UserFriend.friend_user_id == blocked_user), sqlalchemy.and_(UserFriend.user_id == blocked_user, UserFriend.friend_user_id == selected_user)))).scalars().first()

    if friendship:
        db.delete(friendship)

    users_chat: Chat = await backend.routers.chats.utils.get_users_private_chat(selected_user, blocked_user, db)
    if users_chat:
        db.delete(users_chat)

    friend_request_to_blocked: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest).where(sqlalchemy.and_(UserFriendRequest.sender_user_id == selected_user.id, UserFriendRequest.receiver_user_id == blocked_user.id))).scalars().first()
    if friend_request_to_blocked:
        db.delete(friend_request_to_blocked)

    friend_request_from_blocked: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest).where(sqlalchemy.and_(UserFriendRequest.sender_user_id == blocked_user.id, UserFriendRequest.receiver_user_id == selected_user.id))).scalars().first()
    if friend_request_from_blocked:
        db.delete(friend_request_from_blocked)

    db.add(new_block)
    db.commit()
    db.refresh(new_block)

    return fastapi.responses.JSONResponse({"id": new_block.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def delete_blocked_user(
    blocked_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    user_block: BlockedUser = await utils.get_user_block(selected_user, blocked_user, db)

    if not user_block:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)

    db.delete(user_block)
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)