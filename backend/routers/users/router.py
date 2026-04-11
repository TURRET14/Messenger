import fastapi
import sqlalchemy.ext.asyncio

from backend.routers.users import service
import backend.routers.dependencies
from backend.routers.users.response_models import CurrentUserResponseModel, FriendUserInListResponseModel
from backend.storage import *

from backend.routers.users.request_models import (
    RegisterRequestModel,
    LoginRequestModel,
    SessionRequestModel,
    UserUpdateRequestModel,
    UserUpdateLoginRequestModel,
    UserUpdatePasswordRequestModel, CodeModel, EmailRequestModel)

from backend.routers.users.response_models import (
    UserInListResponseModel,
    UserResponseModel,
    FriendRequestResponseModel,
    LoginResponseModel,
    SessionResponseModel)

from backend.routers.common_models import (IDModel)


users_router = fastapi.APIRouter()

@users_router.post("/users/register", response_class = fastapi.responses.Response,
description =
"""
Маршрут запроса на регистрацию пользователя.
В случае прохождения входными данными валидации пользователю на указанную электронную почту отправляется код подтверждения регистрации. Код и данные регистрации хранятся в Redis.
""")
async def register(
    data: RegisterRequestModel = fastapi.Body(),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.register(data, redis_client, db)


@users_router.post("/users", response_class = fastapi.responses.JSONResponse, response_model = IDModel,
description =
"""
Маршрут ввода отправленного на электронную почту кода подтверждения регистрации и создания нового пользователя при прохождении данными повторной валидации.
""")
async def create_user(
    data: CodeModel = fastapi.Body(),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.create_user(data, redis_client, db)


@users_router.post("/login", response_class = fastapi.responses.Response,
description =
"""
Маршрут входа пользователя в систему с указанным логином и паролем и получения сессионного токена, который хранится в Cookie и Redis.
""")
async def login(
    request: fastapi.Request,
    data: LoginRequestModel = fastapi.Body(),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.login(request, data, db, redis_client)


@users_router.get("/users/me/sessions", response_class = fastapi.responses.JSONResponse, response_model = list[SessionResponseModel],
description =
"""
Маршрут получения данных всех действительных сессий пользователя с краткой о них информацией.
""")
async def get_all_sessions(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await service.get_all_sessions(current_user, redis_client)


@users_router.delete("/users/me/sessions", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления указанной сессии пользователя по ее токену.
""")
async def delete_session(
    data: SessionRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.delete_session(data, current_user, redis_client)


@users_router.delete("/users/me/sessions/all", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления всех сессий запрашивающего пользователя.
"""
)
async def delete_all_sessions(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(redis_handler.get_redis_client)) -> fastapi.responses.Response:

    return await service.delete_all_sessions(current_user, redis_client)

@users_router.get("/users/id/{user_id}", response_class = fastapi.responses.JSONResponse, response_model = UserResponseModel, dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения информации о указанном пользователе по его ID.
""")
async def get_user(
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id)) -> fastapi.responses.JSONResponse:

    return await service.get_user(selected_user, False)


@users_router.get("/users/me", response_class = fastapi.responses.JSONResponse, response_model = CurrentUserResponseModel,
description =
"""
Маршрут получения информации о текущем пользователе.
""")
async def get_current_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)) -> fastapi.responses.JSONResponse:

    return await service.get_user(current_user, True)


@users_router.get("/users/me/login", response_class = fastapi.responses.JSONResponse, response_model = LoginResponseModel,
description =
"""
Маршрут получения логина текущего пользователя.
""")
async def get_current_user_login(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user)) -> fastapi.responses.JSONResponse:

    return await service.get_user_login(current_user)


@users_router.patch("/users/me", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления всех данных профиля текущего пользователя (Кроме логина, пароля и фотографии профиля)
""")
async def update_user(
    user_data: UserUpdateRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user(user_data, current_user, db)


@users_router.patch("/users/me/email", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления адреса электронной почты текущего пользователя.
Если новый адрес электронной почты не занят, на нее отправляется письмо с кодом подтверждения.
""")
async def update_user_email(
    email_data: EmailRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_email(email_data, current_user, redis_client, db)


@users_router.patch("/users/me/email/confirm", response_class = fastapi.responses.Response,
description =
"""
Маршрут подтверждения обновления адреса электронной почты пользователя путем ввода кода подтверждения, отправленного на новую электронную почту.
""")
async def confirm_update_user_email(
    code_data: CodeModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.confirm_update_user_email(code_data, current_user, redis_client, db)


@users_router.put("/users/me/login", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления логина текущего пользователя.
""")
async def update_user_login(
    user_login_data: UserUpdateLoginRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_login(user_login_data, current_user, db)


@users_router.put("/users/me/password", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления пароля текущего пользователя.
""")
async def update_user_password(
    user_password_data: UserUpdatePasswordRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_password(user_password_data, current_user, db)


@users_router.get("/users/id/{user_id}/avatar", response_class = fastapi.responses.StreamingResponse, dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения фотографии профиля указанного пользователя.
""")
async def get_user_avatar(
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await service.get_user_avatar(selected_user, minio_client)


@users_router.get("/users/me/avatar", response_class = fastapi.responses.StreamingResponse,
description =
"""
Маршрут получения фотографии профиля текущего пользователя.
""")
async def get_current_user_avatar(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client)) -> fastapi.responses.StreamingResponse:

    return await service.get_user_avatar(current_user, minio_client)


@users_router.put("/users/me/avatar", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления фотографии профиля текущего пользователя.
""")
async def update_user_avatar(
    file: fastapi.UploadFile = fastapi.File(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_user_avatar(current_user, file, minio_client, db)


@users_router.delete("/users/me/avatar", response_class = fastapi.responses.Response,
description =
"""
Маршрут сброса фотографии профиля текущего пользователя.
""")
async def delete_user_avatar(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.delete_user_avatar(current_user, minio_client, db)


@users_router.delete("/users/me", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления текущего пользователя.
""")
async def delete_user(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.delete_user(current_user, minio_client, redis_client, db)


@users_router.get("/users", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения списка всех пользователей (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_users(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_users(offset_multiplier, db)

@users_router.get("/users/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения списка всех пользователей с поиском по Username (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_users_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_users_by_username(offset_multiplier, username, db)


@users_router.get("/users/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[UserInListResponseModel], dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения списка всех пользователей с поиском по Имени, Фамилии и Отчеству (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_users_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(default = None, max_length = 100),
    surname: str | None = fastapi.Query(default = None, max_length = 100),
    second_name: str | None = fastapi.Query(default = None, max_length = 100),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_users_by_names(offset_multiplier, name, surname, second_name, db)


@users_router.get("/users/me/friends", response_class = fastapi.responses.JSONResponse, response_model = list[FriendUserInListResponseModel],
description =
"""
Маршрут получения списка всех друзей пользователя (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_friends(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_friends(offset_multiplier, current_user, db)

@users_router.get("/users/me/friends/search/by-username", response_class = fastapi.responses.JSONResponse, response_model = list[FriendUserInListResponseModel],
description =
"""
Маршрут получения списка всех друзей пользователя с поиском по Username (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_friends_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_friends_by_username(offset_multiplier, username, current_user, db)


@users_router.get("/users/me/friends/search/by-names", response_class = fastapi.responses.JSONResponse, response_model = list[FriendUserInListResponseModel],
description =
"""
Маршрут получения списка всех друзей пользователя с поиском по Имени, Фамилии и Отчеству (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_friends_by_names(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    name: str | None = fastapi.Query(default = None, max_length = 100),
    surname: str | None = fastapi.Query(default = None, max_length = 100),
    second_name: str | None = fastapi.Query(default = None, max_length = 100),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_friends_by_names(offset_multiplier, name, surname, second_name, current_user, db)


@users_router.get("/users/me/friends/requests/sent", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestResponseModel],
description =
"""
Маршрут получения списка всех запросов в друзья, отправленных пользователем (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_sent_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_user_sent_friend_requests(offset_multiplier, current_user, db)


@users_router.get("/users/me/friends/requests/received", response_class = fastapi.responses.JSONResponse, response_model = list[FriendRequestResponseModel],
description =
"""
Маршрут получения списка всех запросов в друзья, полученных пользователем (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_received_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_user_received_friend_requests(offset_multiplier, current_user, db)


@users_router.post("/users/me/friends/requests/send", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут отправки указанному пользователю запроса в друзья.
""")
async def send_friend_request(
    receiver: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.send_friend_request(receiver, current_user, db)


@users_router.put("/users/me/friends/requests/received/id/{friend_request_id}", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут принятия полученного пользователем запроса в друзья по его ID.
""")
async def accept_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.accept_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/requests/received/id/{friend_request_id}", response_class=fastapi.responses.Response,
description =
"""
Маршрут отклонения полученного пользователем запроса в друзья по его ID.
""")
async def decline_received_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.decline_received_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/requests/sent/id/{friend_request_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления отправленного пользователем запроса в друзья по его ID.
""")
async def delete_sent_friend_request(
    friend_request: FriendRequest = fastapi.Depends(backend.routers.dependencies.get_friend_request_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.delete_sent_friend_request(friend_request, current_user, db)


@users_router.delete("/users/me/friends/{friendship_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления указанной дружбы между пользователями по ее ID.
""")
async def delete_friendship(
    friendship: Friendship = fastapi.Depends(backend.routers.dependencies.get_friendship_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.delete_friendship(friendship, current_user, db)


@users_router.post("/users/me/blocks", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут блокировки пользователя по его ID.
""")
async def block_user(
    blocked_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.block_user(blocked_user, current_user, minio_client, redis_client, db)


@users_router.delete("/users/me/blocks/id/{user_block_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут разблокировки пользователя по ID Блокировки.
""")
async def unblock_user(
    user_block: UserBlock = fastapi.Depends(backend.routers.dependencies.get_user_block_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.unblock_user(user_block, current_user, db)


@users_router.get("/users/me/blocks", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут получения блокировок пользователей.
""")
async def get_blocks(
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_blocks(current_user, db)
