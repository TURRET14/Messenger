import fastapi
import sqlalchemy
import sqlalchemy.orm
import secrets
import datetime
import redis
import asyncio

import backend.models.pydantic_request_models
import backend.storage.redis
import backend.storage.database
import backend.authorization.password_hashing
import backend.parameters

async def post_user(
    data: backend.models.pydantic_request_models.RegisterModel,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.username == data.username)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USERNAME_ALREADY_TAKEN_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(
            backend.storage.database.User.email_address == data.email_address)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "EMAIL_ALREADY_TAKEN_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(
            backend.storage.database.User.login == data.login)).scalars().first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "LOGIN_ALREADY_TAKEN_ERROR")

    new_user: backend.storage.database.User = backend.storage.database.User(
    username = data.username,
    name = data.name,
    email_address = data.email_address,
    login = data.login,
    password = backend.authorization.password_hashing.hash_password(data.password),
    surname = data.surname,
    second_name = data.second_name,
    date_and_time_registered = datetime.datetime.now(datetime.timezone.utc),
    messenger_role = backend.storage.database.SystemRoles.user)

    db.add(new_user)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_201_CREATED)


async def post_login(
    data: backend.models.pydantic_request_models.LoginModel,
    response: fastapi.responses.Response,
    db: sqlalchemy.orm.session.Session,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    selected_user: backend.storage.database.User | None = db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(backend.storage.database.User.login == data.login)).scalars().first()

    if not selected_user:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "LOGIN_DOES_NOT_EXIST_ERROR")

    if backend.authorization.password_hashing.verify_password(selected_user.password, data.password):
        # Добавление сессии в Redis (Новая запись в словарь сессий + Новое значение во множестве сессий пользователя)
        session_id = secrets.token_urlsafe(64)
        expiration_date: int = int(datetime.datetime.now().timestamp()) + int(datetime.timedelta(seconds = backend.parameters.redis_session_expiration_time_seconds).total_seconds())
        coroutines: list = list()
        coroutines.append(redis_client.sadd(f"user:{selected_user.id}:sessions", session_id))
        coroutines.append(redis_client.hset(f"session:{session_id}:data",
        mapping={"user_id": selected_user.id, "expiration_date": expiration_date}))
        coroutines.append(redis_client.expireat(f"user:{selected_user.id}:sessions", expiration_date))
        coroutines.append(redis_client.expireat(f"user:{selected_user.id}:sessions", expiration_date))
        await asyncio.gather(*coroutines)

        response.set_cookie("session_id", value = session_id, max_age = backend.parameters.redis_session_expiration_time_seconds, httponly = True, secure = True, samesite = "strict")

        return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "PASSWORD_IS_INCORRECT_ERROR")


async def delete_session(
    data: backend.models.pydantic_request_models.SessionModel,
    selected_user: backend.storage.database.User,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    # Удаление сессии из Redis (Удаление сессии из словаря сессий + Удаление значения сессии из множества сессий пользователя)
    # Сначала проверяется, принадлежит ли сессия пользователю
    session_data: dict[str, str] = await redis_client.hgetall(f"session:{data.session_id}:data")
    if session_data["user_id"] != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_SESSION_ID_ERROR")

    coroutines: list = list()
    coroutines.append(redis_client.srem(f"user:{selected_user.id}:sessions", data.session_id))
    coroutines.append(redis_client.delete(f"session:{data.session_id}:data"))
    await asyncio.gather(*coroutines)

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)


async def delete_all_sessions(
    selected_user: backend.storage.database.User,
    redis_client: redis.Redis) -> fastapi.responses.JSONResponse:

    # Удаление всех сессий пользователя из Redis (Удаление всех сессий пользователя из словаря сессий + Удаление множества сессий пользователя)
    user_sessions: set = await redis_client.smembers(f"user:{selected_user.id}:sessions")
    coroutines: list = list()
    for session_id in user_sessions:
        coroutines.append(redis_client.delete(f"session:{session_id}:data"))
    await asyncio.gather(*coroutines)
    await redis_client.delete(f"user:{selected_user.id}:sessions")

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)