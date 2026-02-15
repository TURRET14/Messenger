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
import redis
import secrets
import asyncio

import backend.dependencies
import backend.password_hashing
import backend.parameters
from backend.return_details import *
from backend.storage import *
import models

async def create_user(
    data: models.RegisterModel,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if db.execute(sqlalchemy.select(User).where(User.username == data.username)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.username_already_taken_error)

    if db.execute(sqlalchemy.select(User).where(User.email_address == data.email_address)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.email_already_taken_error)

    if db.execute(sqlalchemy.select(User).where(User.login == data.login)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.login_already_taken_error)

    new_user: User = User(
    username = data.username,
    name = data.name,
    email_address = data.email_address,
    login = data.login,
    password = backend.password_hashing.hash_password(data.password),
    surname = data.surname,
    second_name = data.second_name,
    date_and_time_registered = datetime.datetime.now(datetime.timezone.utc))

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return fastapi.responses.JSONResponse({"id": new_user.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def login(
    data: models.LoginModel,
    response: fastapi.responses.Response,
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    selected_user: User = db.execute(sqlalchemy.select(User)
    .where(User.login == data.login)).scalars().first()

    if not selected_user:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.incorrect_login_error)

    if backend.password_hashing.verify_password(selected_user.password, data.password):
        # Добавление сессии в Redis (Новая запись в словарь сессий + Новое значение во множестве сессий пользователя)
        session_id = secrets.token_urlsafe(64)
        expiration_date: int = int(datetime.datetime.now().timestamp()) + int(datetime.timedelta(seconds = backend.parameters.redis_session_expiration_time_seconds).total_seconds())

        coroutines: list = list()
        coroutines.append(redis_client.sadd(f"user:{selected_user.id}:sessions", session_id))
        coroutines.append(redis_client.hset(f"session:{session_id}:data",
        mapping = {"user_id": selected_user.id, "expiration_date": expiration_date}))
        coroutines.append(redis_client.expireat(f"user:{selected_user.id}:sessions", expiration_date))
        coroutines.append(redis_client.expireat(f"user:{selected_user.id}:sessions", expiration_date))

        await asyncio.gather(*coroutines)

        response.set_cookie("session_id", value = session_id, max_age = backend.parameters.redis_session_expiration_time_seconds, httponly = True, secure = True, samesite = "strict")

        return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.incorrect_password_error)


async def delete_session(
    data: models.SessionModel,
    selected_user: User,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    # Удаление сессии из Redis (Удаление сессии из словаря сессий + Удаление значения сессии из множества сессий пользователя)
    # Сначала проверяется, принадлежит ли сессия пользователю
    session: dict[str, str] = await redis_client.hgetall(f"session:{data.session_id}:data")

    if session["user_id"] != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.invalid_session_id_error)

    coroutines: list = list()
    coroutines.append(redis_client.srem(f"user:{selected_user.id}:sessions", data.session_id))
    coroutines.append(redis_client.delete(f"session:{data.session_id}:data"))

    await asyncio.gather(*coroutines)

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def delete_all_sessions(
    selected_user: User,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    # Удаление всех сессий пользователя из Redis (Удаление всех сессий пользователя из словаря сессий + Удаление множества сессий пользователя)
    session_list: set = await redis_client.smembers(f"user:{selected_user.id}:sessions")

    coroutines: list = list()
    for session_id in session_list:
        coroutines.append(redis_client.delete(f"session:{session_id}:data"))

    await asyncio.gather(*coroutines)
    await redis_client.delete(f"user:{selected_user.id}:sessions")

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def get_user(
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    selected_user: dict = {
        "id": selected_user.id,
        "username": selected_user.username,
        "name": selected_user.name,
        "surname": selected_user.surname,
        "second_name": selected_user.second_name,
        "date_of_birth": selected_user.date_of_birth,
        "gender": selected_user.gender,
        "email_address": selected_user.email_address,
        "phone_number": selected_user.phone_number,
        "about": selected_user.about,
        "date_and_time_registered": selected_user.date_and_time_registered
    }

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_user), status_code = fastapi.status.HTTP_200_OK)


async def get_user_login(
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    user_login: dict = {"login": selected_user.login}

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_login), status_code = fastapi.status.HTTP_200_OK)


async def update_user(
    data: models.UserUpdateModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if db.execute(sqlalchemy.select(User)
    .where(sqlalchemy.and_(User.username == data.username, User.id != selected_user.id))).scalars().first() is not None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.username_already_taken_error)

    if db.execute(sqlalchemy.select(User)
    .where(sqlalchemy.and_(User.email_address == data.email_address, User.id != selected_user.id))).scalars().first() is not None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.email_already_taken_error)

    if db.execute(sqlalchemy.select(User)
    .where(sqlalchemy.and_(User.phone_number == data.phone_number, User.id != selected_user.id))).scalars().first() is not None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.phone_number_already_taken_error)

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

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def update_user_login(
    data: models.UserUpdateLoginModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if db.execute(sqlalchemy.select(User)
    .where(sqlalchemy.and_(User.login == selected_user.login, User.id != selected_user.id))).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.login_already_taken_error)

    selected_user.login = data.login
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def update_user_password(
    data: models.UserUpdatePasswordModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if backend.password_hashing.verify_password(selected_user.password, data.old_password):
        selected_user.password = backend.password_hashing.hash_password(data.new_password)
        db.commit()

        return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_PASSWORD_ERROR")

async def get_user_avatar(
    selected_user: User,
    minio_client: minio.Minio) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    if not selected_user.avatar_photo_path:
        return fastapi.responses.FileResponse(backend.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)

    file = minio_client.get_object("users:avatars", selected_user.avatar_photo_path)
    file_stat = minio_client.stat_object("users:avatars", selected_user.avatar_photo_path)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def update_user_avatar(
    selected_user: User,
    file: fastapi.UploadFile,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if file.content_type not in backend.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_type_not_allowed_error)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_type_not_allowed_error)

    if file.size > backend.parameters.max_avatar_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_size_too_large_error)

    #MinIO - Загрузка аватара
    minio_file_name: str = f"users/{selected_user.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("users:avatars", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)

    # MinIO - Удаление старого аватара
    if not selected_user.avatar_photo_path:
        minio_client.remove_object("users:avatars", selected_user.avatar_photo_path)

    selected_user.avatar_photo_path = minio_file_name
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code=fastapi.status.HTTP_200_OK)


async def delete_user(
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_user.avatar_photo_path:
        minio_client.remove_object("users:avatars", selected_user.avatar_photo_path)

    user_chats: Sequence[Chat] = db.execute(sqlalchemy.select(Chat).where(Chat.owner_user_id == selected_user.id)).scalars().all()

    for chat in user_chats:
        if chat.avatar_photo_path:
            minio_client.remove_object("groups:avatars", chat.avatar_photo_path)

    db.delete(selected_user)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def get_users(
    offset_multiplier: int,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    users_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .order_by(User.id).offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)


async def search_users_by_username(
    offset_multiplier: int,
    username: str,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    users_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .where(User.username.like(f"%{username}"))
    .order_by(User.id).offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def search_users_by_names(
    offset_multiplier: int,
    name: str | None,
    surname: str | None,
    second_name: str | None,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if name is None and surname is None and second_name is None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

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

    users_list: Sequence[sqlalchemy.RowMapping] = db.execute(select_request.order_by(User.id)
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def get_friends(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friends_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
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
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_username(
    offset_multiplier: int,
    username: str,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friends_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
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
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_names(
    offset_multiplier: int,
    name: str | None,
    surname: str | None,
    second_name: str | None,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if name is None and surname is None and second_name is None:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not name:
        name = str()
    if not surname:
        surname = str()
    if not second_name:
        second_name = str()

    friends_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
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
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_sent_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.user_not_found_error)

    friend_requests_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    UserFriendRequest.id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    UserFriendRequest.date_and_time_sent)
    .select_from(UserFriendRequest)
    .where(UserFriendRequest.sender_user_id == selected_user.id)
    .join(User, User.id == UserFriendRequest.sender_user_id)
    .order_by(User.id)
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_received_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.user_not_found_error)

    friend_requests_list: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    UserFriendRequest.id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    UserFriendRequest.date_and_time_sent)
    .select_from(UserFriendRequest)
    .where(UserFriendRequest.receiver_user_id == selected_user.id)
    .join(User, User.id == UserFriendRequest.sender_user_id)
    .order_by(User.id)
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def send_friend_request(
    receiver: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if receiver.id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)


    if (db.execute(sqlalchemy.select(UserFriendRequest).where(
    sqlalchemy.and_(UserFriendRequest.sender_user_id == selected_user.id,
    UserFriendRequest.receiver_user_id == receiver.id))).scalars().first() or
    db.execute(sqlalchemy.select(UserFriendRequest)
    .where(sqlalchemy.and_(UserFriendRequest.sender_user_id == receiver.id,
    UserFriendRequest.receiver_user_id == selected_user.id))).scalars().first() is not None):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.conflict_error)

    if db.execute(sqlalchemy.select(UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == selected_user.id,
    UserFriend.friend_user_id == receiver.id), sqlalchemy.and_(UserFriend.user_id == receiver.id,
    UserFriend.friend_user_id == selected_user.id)))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.conflict_error)

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
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.object_not_found_error)

    if friend_request.receiver_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.unauthorized_error)

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

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.user_not_found_error)

    friend_request: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest)
    .where(UserFriendRequest.id == friend_request_id)).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.object_not_found_error)

    if friend_request.receiver_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.unauthorized_error)

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def delete_sent_friend_request(
    friend_request_id: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.user_not_found_error)

    friend_request: UserFriendRequest = db.execute(sqlalchemy.select(UserFriendRequest)
    .where(UserFriendRequest.id == friend_request_id)).scalars().first()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.object_not_found_error)

    if friend_request.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = ExceptionDetails.unauthorized_error)

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def delete_friend(
    friend: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friendship: UserFriend = db.execute(sqlalchemy.select(UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(UserFriend.user_id == selected_user.id, UserFriend.friend_user_id == friend.id),
    sqlalchemy.and_(UserFriend.user_id == friend.id, UserFriend.friend_user_id == selected_user.id)))).scalars().first()

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = ExceptionDetails.object_not_found_error)

    db.delete(friendship)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)