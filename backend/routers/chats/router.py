import fastapi
import sqlalchemy.orm
import minio

import backend.routers.chats.implementation
import backend.dependencies
import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.minio_handler
import backend.storage.database
import backend.storage.redis_handler
from backend import dependencies

chats_router = fastapi.APIRouter()


@chats_router.get("/", response_class = fastapi.responses.JSONResponse, response_model = list[backend.models.pydantic_response_models.ChatModel])
async def get_all_current_user_chats(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.get_all_user_chats(offset_multiplier, current_user, db)


@chats_router.get("/chats/id/{chat_id}", response_class = fastapi.responses.JSONResponse, response_model = backend.models.pydantic_response_models.ChatModel)
async def get_chat(
    chat_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await get_chat(chat_id, current_user, db)


@chats_router.get("/chats/id/{chat_id}/users", response_class = fastapi.responses.JSONResponse, response_model = list[backend.models.pydantic_response_models.ChatUserModel])
async def get_chat_users(
    chat_id: int = fastapi.Path(ge = 0),
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.get_chat_users(chat_id, offset_multiplier, current_user, db)


@chats_router.get("/chats/id/{chat_id}/last-message", response_class = fastapi.responses.JSONResponse, response_model = backend.models.pydantic_response_models.MessageModel)
async def get_chat_last_message(
    chat_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.get_chat_last_message(chat_id, current_user, db)


@chats_router.get("/chats/id/{chat_id}/avatar")
async def get_chat_avatar(
    chat_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(backend.storage.minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    return await backend.routers.chats.implementation.get_chat_avatar(chat_id, current_user, minio_client, db)


@chats_router.post("/chats/private", response_class = fastapi.responses.JSONResponse)
async def create_private_chat(
    data: backend.models.pydantic_request_models.IDModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.create_private_chat(data, current_user, db)


@chats_router.post("/chats/group", response_class = fastapi.responses.JSONResponse)
async def create_group_chat(
    data: backend.models.pydantic_request_models.GroupChatModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.create_group_chat(data, current_user, db)


@chats_router.put("/chats/id/{chat_id}/avatar")
async def update_chat_avatar(
    chat_id: int = fastapi.Path(ge = 0),
    file: fastapi.UploadFile = fastapi.File(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(backend.storage.minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.update_chat_avatar(chat_id, file, current_user, minio_client, db)


@chats_router.patch("/chats/id/{chat_id}/name")
async def update_chat_name(
    chat_id: int = fastapi.Path(ge = 0),
    data: backend.models.pydantic_request_models.GroupChatModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.update_chat_name(chat_id, data, current_user, db)


@chats_router.patch("/chats/id/{chat_id}/owner")
async def update_chat_owner(
    chat_id: int = fastapi.Path(ge=0),
    data: backend.models.pydantic_request_models.IDModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.update_chat_owner(chat_id, data, current_user, db)


@chats_router.post("/chats/id/{chat_id}/admins")
async def add_chat_admin(
    chat_id: int = fastapi.Path(ge=0),
    data: backend.models.pydantic_request_models.IDModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.add_chat_admin(chat_id, data, current_user, db)


@chats_router.delete("/chats/id/{chat_id}/admins/id/{admin_user_id}")
async def delete_chat_admin(
    chat_id: int = fastapi.Path(ge=0),
    admin_user_id: int = fastapi.Path(ge=0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.delete_chat_admin(chat_id, admin_user_id, current_user, db)


@chats_router.post("/chats/id/{chat_id}/users")
async def add_chat_user(
    chat_id: int = fastapi.Path(ge=0),
    data: backend.models.pydantic_request_models.IDModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.add_chat_user(chat_id, data, current_user, db)


@chats_router.delete("/chats/id/{chat_id}/users/id/{chat_user_id}")
async def delete_chat_user(
    chat_id: int = fastapi.Path(ge=0),
    chat_user_id: int = fastapi.Path(ge=0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(
    backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.delete_chat_user(chat_id, chat_user_id, current_user, db)


@chats_router.delete("/chats/id/{chat_id}/users/me}")
async def leave_chat(
    chat_id: int = fastapi.Path(ge=0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.leave_chat(chat_id, current_user, db)


@chats_router.delete("/chats/id/{chat_id}", response_class = fastapi.responses.JSONResponse)
async def delete_chat(
    chat_id: int = fastapi.Path(ge=0),
    current_user: backend.storage.database.User = fastapi.Depends(dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(backend.storage.minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.routers.chats.implementation.delete_chat(chat_id, current_user, minio_client, db)

