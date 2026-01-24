import fastapi
import sqlalchemy
import sqlalchemy.orm
import secrets
import datetime

import backend.models.pydantic_request_models
import backend.storage.redis
import backend.storage.database
import backend.authorization.password_hashing
import backend.parameters

async def post_register(
    data: backend.models.pydantic_request_models.RegisterModel,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.username == data.username)).first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USERNAME_ALREADY_TAKEN_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(
            backend.storage.database.User.email_address == data.email_address)).first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "EMAIL_ALREADY_TAKEN_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(
            backend.storage.database.User.login == data.login)).first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "LOGIN_ALREADY_TAKEN_ERROR")

    new_user: backend.storage.database.User = backend.storage.database.User(
    username = data.username,
    name = data.name,
    email_address = data.email_address,
    login = data.login,
    password = backend.authorization.password_hashing.hash_password(data.password),
    surname = data.surname,
    second_name = data.second_name,
    date_and_time_registered = datetime.datetime.now(datetime.timezone.utc))

    db.add(new_user)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_201_CREATED)


async def post_login(
    data: backend.models.pydantic_request_models.LoginModel,
    response: fastapi.responses.Response,
    db: sqlalchemy.orm.session.Session,
    redis_client: backend.storage.redis.RedisClient) -> fastapi.responses.JSONResponse:

    selected_user: backend.storage.database.User | None = (db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(backend.storage.database.User.login == data.login)).first())

    if not selected_user:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "LOGIN_DOES_NOT_EXIST")

    if backend.authorization.password_hashing.verify_password(selected_user.password, data.password):
        session_id = secrets.token_urlsafe(64)
        redis_client.add_user_session(selected_user.id, session_id)
        response.set_cookie("session_id", value = session_id, max_age = backend.parameters.redis_session_expiration_time_seconds, httponly = True, samesite = "strict")
        return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)
    else:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "PASSWORD_IS_INCORRECT")