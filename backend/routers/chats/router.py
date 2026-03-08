import fastapi
import minio
import redis.asyncio
import sqlalchemy.orm

from backend.storage import *
from models import *
from backend.routers.common_models import *
from backend.routers.messages.models import MessageResponseModel
import service
import backend.routers.dependencies
from websocket_listeners_router import chats_websocket_listener_router

chats_router = fastapi.APIRouter()
chats_router.include_router(chats_websocket_listener_router)

@chats_router.get("/chats", response_class = fastapi.responses.JSONResponse, response_model = ChatResponseModel)
async def get_all_chats(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_all_chats(offset_multiplier, current_user, db)


@chats_router.get("/chats/id/{chat_id}", response_class = fastapi.responses.JSONResponse, response_model = list[ChatResponseModel])
async def get_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_chat(selected_chat, current_user, db)


@chats_router.get("/chats/id/{chat_id}/users", response_class = fastapi.responses.JSONResponse, response_model = list[ChatUserModel])
async def get_chat_members(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_chat_members(offset_multiplier, selected_chat, current_user, db)


@chats_router.get("/chats/id/{chat_id}/messages/last", response_class = fastapi.responses.JSONResponse, response_model = MessageResponseModel)
async def get_chat_last_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_chat_last_message(selected_chat, current_user, db)


@chats_router.get("/chats/id/{chat_id}/avatar")
async def get_chat_avatar(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    return await backend.routers.chats.service.get_chat_avatar(selected_chat, current_user, minio_client, db)


@chats_router.post("/chats/private", response_class = fastapi.responses.JSONResponse)
async def create_or_join_private_chat(
    friend_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_or_join_private_chat(friend_user, current_user, redis_client, db)


@chats_router.post("/chats/group", response_class = fastapi.responses.JSONResponse)
async def create_group_chat(
    data: GroupChatModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_group_chat(data, current_user, redis_client, db)


@chats_router.put("/chats/id/{chat_id}/avatar", response_class = fastapi.responses.JSONResponse)
async def update_chat_avatar(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    file: fastapi.UploadFile = fastapi.File(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.update_chat_avatar(selected_chat, file, current_user, minio_client, redis_client, db)


@chats_router.patch("/chats/id/{chat_id}/name", response_class = fastapi.responses.JSONResponse)
async def update_chat_name(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    data: GroupChatModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.update_chat_name(selected_chat, data, current_user, redis_client, db)


@chats_router.patch("/chats/id/{chat_id}/owner", response_class = fastapi.responses.JSONResponse)
async def update_chat_owner(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_owner_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.update_chat_owner(selected_chat, new_owner_user, current_user, db)


@chats_router.post("/chats/id/{chat_id}/admins", response_class = fastapi.responses.JSONResponse)
async def add_chat_admin(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_admin_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.add_chat_admin(selected_chat, new_admin_user, current_user, db)


@chats_router.delete("/chats/id/{chat_id}/admins/id/{user_id}", response_class = fastapi.responses.JSONResponse)
async def delete_chat_admin(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    admin_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.delete_chat_admin(selected_chat, admin_user, current_user, db)


@chats_router.post("/chats/id/{chat_id}/users", response_class = fastapi.responses.JSONResponse)
async def add_chat_user(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    new_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_data_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.add_chat_user(selected_chat, new_user, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}/users/id/{user_id}", response_class = fastapi.responses.JSONResponse)
async def delete_chat_user(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    chat_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.delete_chat_user(selected_chat, chat_user, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}/users/me}", response_class = fastapi.responses.JSONResponse)
async def leave_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.leave_chat(selected_chat, current_user, redis_client, db)


@chats_router.delete("/chats/id/{chat_id}", response_class = fastapi.responses.JSONResponse)
async def delete_chat(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.delete_chat(selected_chat, current_user, minio_client, redis_client, db)


@chats_router.post("/chats/communities", response_class = fastapi.responses.JSONResponse)
async def create_community(
    data: GroupChatModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: redis.asyncio.Redis = fastapi.Depends(get_redis_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.create_community(data, current_user, redis_client, db)


@chats_router.get("/chats/id/{chat_id}/messages/id/{message_id}/discussion")
async def get_discussion_by_community_message_id(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_discussion_by_community_message_id(selected_chat, selected_message, current_user, db)


@chats_router.get("/chats/walls/users/id/{user_id}", response_class = fastapi.responses.JSONResponse, response_model = ChatResponseModel)
async def get_user_wall(
    wall_user: User = fastapi.Depends(backend.routers.dependencies.get_user_by_path_user_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_user_wall(wall_user, current_user, db)


@chats_router.get("/chats/id/{chat_id}/chat-users/id/{chat_user_id}")
async def get_chat_user(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_chat_user: ChatUser = fastapi.Depends(backend.routers.dependencies.get_chat_user_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.service.get_chat_user(selected_chat, selected_chat_user, current_user, db)