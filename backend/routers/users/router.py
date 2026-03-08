import fastapi
import minio
import sqlalchemy.orm
import redis.asyncio

from models import *
import service
import backend.routers.dependencies
from backend.storage import *


users_router = fastapi.APIRouter()


@users_router.post("/users", response_class = fastapi.responses.JSONResponse)
async def create_user(
    data: RegisterModel = fastapi.Body(),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.create_user(data, db)


@users_router.post("/login", response_class = fastapi.responses.JSONResponse)
async def login(
    data: LoginModel = fastapi.Body(),
    response: fastapi.responses.Response = fastapi.responses.Response(),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db),
    redis_client: redis.asyncio.Redis = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.login(data, response, db, redis_client)


@users_router.delete("/users/me/sessions/current", response_class = fastapi.responses.JSONResponse)
async def delete_session(
    data: SessionModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_session(data, current_user, redis_client)


@users_router.delete("/users/me/sessions/all", response_class = fastapi.responses.JSONResponse)
async def delete_all_sessions(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_all_sessions(current_user, redis_client)

@users_router.get("/users/id/{user_id}", response_class = fastapi.responses.JSONResponse, response_model = UserResponseModel)
async def get_user(
    user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user(user, db)


@users_router.get("/users/me", response_class = fastapi.responses.JSONResponse, response_model = UserResponseModel)
async def get_current_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user(current_user, db)


@users_router.get("/users/me/login", response_class = fastapi.responses.JSONResponse, response_model = LoginResponseModel)
async def get_current_user_login(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user_login(current_user, db)


@users_router.patch("/users/me", response_class = fastapi.responses.JSONResponse)
async def update_user(
    data: UserUpdateModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.update_user(data, current_user, db)


@users_router.put("/users/me/login", response_class = fastapi.responses.JSONResponse)
async def update_user_login(
    data: UserUpdateLoginModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.update_user_login(data, current_user, db)


@users_router.put("/users/me/password", response_class = fastapi.responses.JSONResponse)
async def update_user_password(
    data: UserUpdatePasswordModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.update_user_password(data, current_user, db)

@users_router.get("/users/id/{user_id}/avatar", response_class = fastapi.responses.StreamingResponse)
async def get_user_avatar(
    user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await backend.routers.users.service.get_user_avatar(user, minio_client)


@users_router.get("/users/me/avatar", response_class = fastapi.responses.StreamingResponse)
async def get_current_user_avatar(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    return await backend.routers.users.service.get_user_avatar(current_user, minio_client)


@users_router.put("/users/me/avatar", response_class = fastapi.responses.JSONResponse)
async def update_user_avatar(
    file: fastapi.UploadFile = fastapi.File(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.update_user_avatar(current_user, file, minio_client, db)


@users_router.delete("/users/me", response_class = fastapi.responses.JSONResponse)
async def delete_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_user(current_user, minio_client, db)


@users_router.get("/users", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def get_users(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_users(offset_multiplier, db)

@users_router.get("/users/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_users_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_users_by_username(offset_multiplier, username, db)


@users_router.get("/users/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_users_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(max_length = 100),
    surname: str | None = fastapi.Query(max_length = 100),
    second_name: str | None = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_users_by_names(offset_multiplier, name, surname, second_name, db)


@users_router.get("/users/me/friends", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def get_friends(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_friends(offset_multiplier, current_user, db)

@users_router.get("/users/me/friends/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_friends_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_friends_by_username(offset_multiplier, username, current_user, db)


@users_router.get("/users/me/friends/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_friends_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(max_length = 100),
    surname: str | None = fastapi.Query(max_length = 100),
    second_name: str | None = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_friends_by_names(offset_multiplier, name, surname, second_name, current_user, db)


@users_router.get("/users/me/friends/requests/sent", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestUserInListResponseModel])
async def get_sent_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user_sent_friend_requests(offset_multiplier, current_user, db)


@users_router.get("/users/me/friends/requests/received", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestUserInListResponseModel])
async def get_received_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user_received_friend_requests(offset_multiplier, current_user, db)


@users_router.post("/users/me/friends/requests/sent", response_class = fastapi.responses.JSONResponse)
async def send_friend_request(
    receiver: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.send_friend_request(receiver, current_user, db)


@users_router.put("/users/me/friends/requests/received/id/{friend_request_id}", response_class = fastapi.responses.JSONResponse)
async def accept_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.accept_friend_request(friend_request_id, current_user, db)


@users_router.delete("/users/me/friends/requests/received/id/{friend_request_id}", response_class=fastapi.responses.JSONResponse)
async def decline_received_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.decline_received_friend_request(friend_request_id, current_user, db)


@users_router.delete("/users/me/friends/requests/sent/id/{friend_request_id}", response_class = fastapi.responses.JSONResponse)
async def delete_sent_friend_request(
    friend_request_id: int = fastapi.Path(ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_sent_friend_request(friend_request_id, current_user, db)


@users_router.delete("/users/me/friends/id/{friend_user_id}", response_class = fastapi.responses.JSONResponse)
async def delete_friend(
    friend: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_friend(friend, current_user, db)


@users_router.post("/users/me/blocked-users", response_class = fastapi.responses.JSONResponse)
async def add_blocked_user(
    blocked_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.add_blocked_user(blocked_user, current_user, db)


@users_router.delete("/users/me/blocked-users", response_class = fastapi.responses.JSONResponse)
async def delete_blocked_user(
    blocked_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.delete_blocked_user(blocked_user, current_user, db)