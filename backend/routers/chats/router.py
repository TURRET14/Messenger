import fastapi
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.chats.request_models import (ChatNameRequestModel)
from backend.routers.chats.response_models import (ChatResponseModel, ChatMembershipResponseModel)
from backend.routers.chats import service
import backend.routers.dependencies

chats_router = fastapi.APIRouter()

@chats_router.get("/chats", response_class = fastapi.responses.JSONResponse, response_model = ChatResponseModel,
description =
"""
Маршрут получения списка всех чатов текущего пользователя (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_all_chats(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_all_chats(offset_multiplier, current_user, db)


@chats_router.get("/chats/id/{chat_id}", response_class = fastapi.responses.JSONResponse, response_model = list[ChatResponseModel],
description =
"""
Маршрут получения подробной информации об указанном чате.
""")
async def get_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat(selected_chat, current_user, db)


@chats_router.get("/chats/id/{chat_id}/memberships", response_class = fastapi.responses.JSONResponse, response_model = list[ChatMembershipResponseModel],
description =
"""
Маршрут получения всех участников указанного чата с информацией об их ролях (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_chat_members(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat_members(offset_multiplier, selected_chat, current_user, db)


@chats_router.get("/chats/id/{chat_id}/avatar", response_class = fastapi.responses.StreamingResponse,
description =
"""
Маршрут получения файла аватара указанного чата, если такой присутствует.
Только для групповых чатов и каналов.
""")
async def get_chat_avatar(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.StreamingResponse:

    return await service.get_chat_avatar(selected_chat, current_user, minio_client, db)


@chats_router.post("/chats/private", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут создания приватного чата (Чата между двумя участниками).
Этот чат не имеет имени, аватарки и владельца. Если участник выходит из чата, то чат удаляется.
""")
async def create_private_chat(
    other_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_private_chat(other_user, current_user, redis_client, db)


@chats_router.post("/chats/group", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут создания группового чата.
Этот чат имеет одного участник и более, имеет название, аватарку, владельца и администраторов.
""")
async def create_group_chat(
    data: ChatNameRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_group_chat(data, current_user, redis_client, db)


@chats_router.put("/chats/id/{chat_id}/avatar", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут обновления файла аватара указанного чата.
Только для групповых чатов и каналов.
""")
async def update_chat_avatar(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    file: fastapi.UploadFile = fastapi.File(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.update_chat_avatar(selected_chat, file, current_user, minio_client, redis_client, db)


@chats_router.patch("/chats/id/{chat_id}/name", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления имени указанного чата.
Только для групповых чатов и каналов.
""")
async def update_chat_name(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    data: ChatNameRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.update_chat_name(selected_chat, data, current_user, redis_client, db)


@chats_router.patch("/chats/id/{chat_id}/owner", response_class = fastapi.responses.Response,
description =
"""
Маршрут обновления владельца указанного чата его владельцем.
Только для групповых чатов и каналов.
""")
async def update_chat_owner(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_owner_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.update_chat_owner(selected_chat, new_owner_user, current_user, redis_client, db)


@chats_router.post("/chats/id/{chat_id}/admins", response_class = fastapi.responses.Response,
description =
"""
Маршрут добавления нового администратора в указанный чат его владельцем. Администраторы могут удалять пользователей, изменять название чата и его аватарку.
Только для групповых чатов и каналов.
""")
async def add_chat_admin(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_admin_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.add_chat_admin(selected_chat, new_admin_user, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}/admins/id/{user_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления администратора из указанного чата его владельцем.
Только для групповых чатов и каналов.
""")
async def delete_chat_admin(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    admin_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.delete_chat_admin(selected_chat, admin_user, current_user, redis_client, db)


@chats_router.post("/chats/id/{chat_id}/users", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут добавления нового пользователя в указанный чат текущим участником чата.
Только для групповых чатов и каналов.
""")
async def add_chat_user(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.add_chat_user(selected_chat, new_user, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}/users/id/{user_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления владельцем или администраторами указанного пользователя из указанного чата.
Только для групповых чатов и каналов.
""")
async def delete_chat_user(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    chat_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.delete_chat_user(selected_chat, chat_user, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}/users/me}", response_class = fastapi.responses.Response,
description =
"""
Маршрут покидания указанного чата пользователем.
Только для приватных, групповых чатов и каналов. Владелец не может покинуть чат, только удалить. Если пользователь выйдет из приватного чата, то приватный чат удалится.
""")
async def leave_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.leave_chat(selected_chat, current_user, minio_client, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут удаления указанного чата его владельцем.
Только для групповых чатов и каналов.
""")
async def delete_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await backend.routers.chats.service.delete_chat(selected_chat, current_user, minio_client, redis_client, db)


@chats_router.post("/chats/channels", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут создания нового канала.
Это чат, в котором оставлять сообщения могут только владелец и администраторы. Исключение - комментарии, их к корневым сообщениям могут оставлять все участники чата.
""")
async def create_channel(
    data: ChatNameRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_channel(data, current_user, redis_client, db)


@chats_router.get("users/id/{user_id}/profile", response_class = fastapi.responses.JSONResponse, response_model = ChatResponseModel, dependencies = [fastapi.Depends(backend.routers.dependencies.get_session_user)],
description =
"""
Маршрут получения чата профиля указанного пользователя. Это личная страница, которая есть у всех пользователей, где оставлять сообщения может только он, а комментировать сообщения могут все пользователи.
""")
async def get_user_profile(
    profile_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_user_profile(profile_user, db)


@chats_router.get("/chats/id/{chat_id}/memberships/id/{chat_user_id}",
description =
"""
Маршрут получения данных об указанном членстве в указанном чате.
""")
async def get_chat_membership(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_chat_membership: ChatMembership = fastapi.Depends(backend.routers.dependencies.get_chat_membership_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_chat_membership(selected_chat, selected_chat_membership, current_user, db)