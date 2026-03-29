import fastapi
import sqlalchemy.ext.asyncio

import service
import backend.routers.dependencies
from backend.storage import *

from request_models import (
    RegisterRequestModel,
    LoginRequestModel,
    SessionRequestModel,
    UserUpdateRequestModel,
    UserUpdateLoginRequestModel,
    UserUpdatePasswordRequestModel)

from response_models import (
    UserInListResponseModel,
    UserResponseModel,
    FriendRequestUserInListResponseModel,
    LoginResponseModel,
    SessionResponseModel)

from backend.routers.common_models import (IDModel)


users_router = fastapi.APIRouter()


@users_router.post("/users", response_class = fastapi.responses.JSONResponse, response_model = IDModel)
async def create_user(
    data: RegisterRequestModel = fastapi.Body(),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.create_user(data, db)


@users_router.post("/login", response_class = fastapi.responses.Response)
async def login(
    request: fastapi.Request,
    response: fastapi.Response,
    data: LoginRequestModel = fastapi.Body(),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.login(request, response, data, db, redis_client)


@users_router.get("/users/me/sessions", response_class = fastapi.responses.JSONResponse, response_model = list[SessionResponseModel])
async def get_all_sessions(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await service.get_all_sessions(current_user, redis_client)


@users_router.delete("/users/me/sessions", response_class = fastapi.responses.Response)
async def delete_session(
    data: SessionRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.delete_session(data, current_user, redis_client)


@users_router.delete("/users/me/sessions/all", response_class = fastapi.responses.Response)
async def delete_all_sessions(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.delete_all_sessions(current_user, redis_client)

@users_router.get("/users/id/{user_id}", response_class = fastapi.responses.JSONResponse, response_model = UserResponseModel, dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)])
async def get_user(
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id)) -> fastapi.responses.JSONResponse:

    return await service.get_user(selected_user)


@users_router.get("/users/me", response_class = fastapi.responses.JSONResponse, response_model = UserResponseModel)
async def get_current_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)) -> fastapi.responses.JSONResponse:

    return await service.get_user(current_user)


@users_router.get("/users/me/login", response_class = fastapi.responses.JSONResponse, response_model = LoginResponseModel)
async def get_current_user_login(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)) -> fastapi.responses.JSONResponse:

    return await service.get_user_login(current_user)


@users_router.patch("/users/me", response_class = fastapi.responses.Response)
async def update_user(
    user_data: UserUpdateRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user(user_data, current_user, db)


@users_router.put("/users/me/login", response_class = fastapi.responses.Response)
async def update_user_login(
    user_login_data: UserUpdateLoginRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_login(user_login_data, current_user, db)


@users_router.put("/users/me/password", response_class = fastapi.responses.Response)
async def update_user_password(
    user_password_data: UserUpdatePasswordRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_password(user_password_data, current_user, db)

@users_router.get("/users/id/{user_id}/avatar", response_class = fastapi.responses.StreamingResponse, dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)])
async def get_user_avatar(
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await service.get_user_avatar(selected_user, minio_client)


@users_router.get("/users/me/avatar", response_class = fastapi.responses.StreamingResponse)
async def get_current_user_avatar(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client)) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    return await backend.routers.users.service.get_user_avatar(current_user, minio_client)


@users_router.put("/users/me/avatar", response_class = fastapi.responses.Response)
async def update_user_avatar(
    file: fastapi.UploadFile = fastapi.File(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.update_user_avatar(current_user, file, minio_client, db)


@users_router.delete("/users/me", response_class = fastapi.responses.Response)
async def delete_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.delete_user(current_user, minio_client, db)


@users_router.get("/users", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)])
async def get_users(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_users(offset_multiplier, db)

@users_router.get("/users/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)])
async def search_users_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_users_by_username(offset_multiplier, username, db)


@users_router.get("/users/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)])
async def search_users_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(max_length = 100),
    surname: str | None = fastapi.Query(max_length = 100),
    second_name: str | None = fastapi.Query(max_length = 100),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_users_by_names(offset_multiplier, name, surname, second_name, db)


@users_router.get("/users/me/friends", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def get_friends(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_friends(offset_multiplier, current_user, db)

@users_router.get("/users/me/friends/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_friends_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_friends_by_username(offset_multiplier, username, current_user, db)


@users_router.get("/users/me/friends/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel])
async def search_friends_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(max_length = 100),
    surname: str | None = fastapi.Query(max_length = 100),
    second_name: str | None = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.search_friends_by_names(offset_multiplier, name, surname, second_name, current_user, db)


@users_router.get("/users/me/friends/requests/sent", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestUserInListResponseModel])
async def get_sent_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user_sent_friend_requests(offset_multiplier, current_user, db)


@users_router.get("/users/me/friends/requests/received", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestUserInListResponseModel])
async def get_received_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.get_user_received_friend_requests(offset_multiplier, current_user, db)


@users_router.post("/users/me/friends/requests/sent", response_class = fastapi.responses.JSONResponse)
async def send_friend_request(
    receiver: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.send_friend_request(receiver, current_user, db)


@users_router.put("/users/me/friends/requests/received/id/{friend_request_id}", response_class = fastapi.responses.JSONResponse)
async def accept_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.accept_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/requests/received/id/{friend_request_id}", response_class=fastapi.responses.Response)
async def decline_received_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.decline_received_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/requests/sent/id/{friend_request_id}", response_class = fastapi.responses.Response)
async def delete_sent_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.delete_sent_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/id/{friend_user_id}", response_class = fastapi.responses.Response)
async def delete_friend(
    friend: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.delete_friend(friend, current_user, db)


@users_router.post("/users/me/blocked-users", response_class = fastapi.responses.JSONResponse)
async def block_user(
    blocked_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.users.service.block_user(blocked_user, current_user, db)


@users_router.delete("/users/me/blocked-users", response_class = fastapi.responses.Response)
async def unblock_user(
    blocked_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.users.service.unblock_user(blocked_user, current_user, db)