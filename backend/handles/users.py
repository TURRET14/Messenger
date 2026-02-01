import fastapi
import sqlalchemy.orm

import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.database
import backend.storage.minio
import backend.handles.implementations.users
import backend.authorization.sessions

users_router = fastapi.APIRouter()


@users_router.get("/users/id/{user_id}/data", response_class=fastapi.responses.JSONResponse, response_model=backend.models.pydantic_response_models.UserModel)
async def get_user_by_id(
    user_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.get_user_by_id(user_id, db)


@users_router.get("/users/me/data", response_class=fastapi.responses.JSONResponse, response_model=backend.models.pydantic_response_models.UserModel)
async def get_current_user(
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user)) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(backend.models.pydantic_response_models.UserModel(
    id = current_user.id,
    username = current_user.username,
    name = current_user.name,
    surname = current_user.surname,
    second_name = current_user.second_name,
    date_of_birth = current_user.date_of_birth,
    gender = current_user.gender,
    email_address = current_user.email_address,
    phone_number = current_user.phone_number,
    country = current_user.country,
    city = current_user.city,
    about = current_user.about,
    date_and_time_registered = current_user.date_and_time_registered,
    messenger_role = current_user.messenger_role),
    status_code = fastapi.status.HTTP_200_OK)


@users_router.get("/users/me/login", response_class=fastapi.responses.JSONResponse, response_model=backend.models.pydantic_response_models.UserLoginModel)
async def get_current_user_login(
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user)) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(backend.models.pydantic_response_models.UserLoginModel(login = current_user.login),
    status_code = fastapi.status.HTTP_200_OK)


@users_router.patch("/users/me/data", response_class=fastapi.responses.JSONResponse)
async def update_current_user(
    data: backend.models.pydantic_request_models.UserUpdateModel = fastapi.Body(),
    session_id: str = fastapi.Cookie(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.update_user(data, current_user, db)


@users_router.put("/users/me/login", response_class = fastapi.responses.JSONResponse)
async def update_current_user_login(
    data: backend.models.pydantic_request_models.UserUpdateLoginModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.update_user_login(data, current_user, db)


@users_router.put("/users/me/password", response_class=fastapi.responses.JSONResponse)
async def update_current_user_password(
    data: backend.models.pydantic_request_models.UserUpdatePasswordModel = fastapi.Body(),
    session_id: str = fastapi.Cookie(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.update_user_password(data, current_user, db)

@users_router.get("/users/id/{user_id}/avatar", response_class=fastapi.responses.StreamingResponse)
async def get_user_avatar_by_id(
    user_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await backend.handles.implementations.users.get_user_avatar_by_id(user_id, minio_client)


@users_router.get("/users/me/avatar", response_class=fastapi.responses.StreamingResponse)
async def get_current_user_avatar(
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await backend.handles.implementations.users.get_user_avatar_by_id(current_user, minio_client)


@users_router.put("/users/me/avatar", response_class=fastapi.responses.JSONResponse)
async def update_current_user_avatar(
    file: fastapi.UploadFile = fastapi.File(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.update_user_avatar(current_user, file, minio_client, db)


@users_router.delete("/users/me", response_class=fastapi.responses.JSONResponse)
async def delete_current_user(
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.delete_user(current_user, minio_client, db)


@users_router.get("/users/search/username", response_class=fastapi.responses.JSONResponse, response_model=list[backend.models.pydantic_response_models.UserInListModel])
async def get_users_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return backend.handles.implementations.users.get_users_by_username(offset_multiplier, username, db)


@users_router.get("/users/search/names", response_class=fastapi.responses.JSONResponse, response_model=list[backend.models.pydantic_response_models.UserInListModel])
async def get_users_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(),
    surname: str | None = fastapi.Query(),
    second_name: str | None = fastapi.Query(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.get_users_by_names(offset_multiplier, name, surname, second_name, db)


@users_router.get("/users/me/friends", response_class=fastapi.responses.JSONResponse, response_model=list[backend.models.pydantic_response_models.UserInListModel])
async def get_current_user_friends(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.get_user_friends(offset_multiplier, current_user, db)


@users_router.get("/users/me/friends/requests/sent", response_class=fastapi.responses.JSONResponse, response_model=list[backend.models.pydantic_response_models.FriendRequestUserInListModel])
async def get_current_user_sent_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.get_user_sent_friend_requests(offset_multiplier, current_user, db)


@users_router.get("/users/me/friends/requests/received", response_class=fastapi.responses.JSONResponse, response_model=list[backend.models.pydantic_response_models.FriendRequestUserInListModel])
async def get_current_user_received_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.get_user_received_friend_requests(offset_multiplier, current_user, db)


@users_router.post("/users/me/friends/requests/sent", response_class=fastapi.responses.JSONResponse)
async def current_user_send_friend_request(
    data: backend.models.pydantic_request_models.IDModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.send_friend_request(data, current_user, db)


@users_router.put("/users/me/friends/requests/received/id/{friend_request_id}", response_class=fastapi.responses.JSONResponse)
async def current_user_accept_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.accept_friend_request(friend_request_id, current_user, db)


@users_router.delete("/users/me/friends/requests/received/id/{friend_request_id}", response_class=fastapi.responses.JSONResponse)
async def current_user_decline_received_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.decline_received_friend_request(friend_request_id, current_user, db)


@users_router.delete("/users/me/friends/requests/sent/{friend_request_id}", response_class=fastapi.responses.JSONResponse)
async def current_user_delete_sent_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.users.delete_sent_friend_request(friend_request_id, current_user, db)