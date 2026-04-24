import fastapi
import sqlalchemy.ext.asyncio

from backend.routers.messages.response_models import LastMessageResponseModel
from backend.storage import *
from backend.routers.messages.request_models import (MessageRequestModel, MessagePostRequestModel)
from backend.routers.messages.response_models import (MessageResponseModel)
from backend.routers.messages import service
import backend.routers.dependencies


messages_router = fastapi.APIRouter()


@messages_router.get("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse, response_model = list[MessageResponseModel],
description =
"""
Маршрут для получения всех сообщений в корне указанного чата (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_chat_messages(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat_messages(offset_multiplier, selected_chat, current_user, db)


@messages_router.get("/chats/id/{chat_id}/messages/id/{message_id}/comments", response_class = fastapi.responses.JSONResponse, response_model = list[MessageResponseModel],
description =
"""
Маршрут для получения всех сообщений в комментариях указанного чата указанного корневого (Parent) сообщения (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def get_chat_message_comments(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat_message_comments(offset_multiplier, selected_chat, selected_message, current_user, db)


@messages_router.get("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.JSONResponse, response_model = MessageResponseModel,
description =
"""
Маршрут для получения данных об указанном сообщении в указанном чате.
""")
async def get_chat_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat_message(selected_chat, selected_message, current_user, db)


@messages_router.post("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут для отправки сообщения в указанный чат с указанными файловыми вложениями, которые удалить или изменить после отдельно не получится.
""")
async def post_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    form_data: MessagePostRequestModel = fastapi.Depends(backend.routers.dependencies.get_post_message_data_from_form),
    file_attachments_list: list[fastapi.UploadFile] = fastapi.File(default = list()),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.post_message(selected_chat, form_data, file_attachments_list, current_user, minio_client, redis_client, db)


@messages_router.delete("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут для удаления указанного сообщения в указанном чате и всех его файловых вложений.
Удалять сообщения может только их автор, единственное исключение - если чат является профилем или каналом, удалять любые сообщения может владелец чата.
""")
async def delete_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(get_minio_client),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.delete_message(selected_chat, selected_message, current_user, minio_client, redis_client, db)


@messages_router.put("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.Response,
description =
"""
Маршрут для обновления указанного сообщения в указанном чате, а точнее только его текста.
Обновлять сообщения может только их автор.
""")
async def update_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    data: MessageRequestModel = fastapi.Body(),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.update_message(selected_chat, selected_message, data, current_user, redis_client, db)

@messages_router.get("/chats/id/{chat_id}/messages/search",
description =
"""
Маршрут для получения всех сообщений в указанном чате с полнотекстовым поиском по тексту сообщения (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_messages_in_chat(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    message_text: str = fastapi.Query(),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_messages_in_chat(offset_multiplier, message_text, selected_chat, current_user, db)


@messages_router.get("/chats/id/{chat_id}/messages/id/{message_id}/comments/search", response_class = fastapi.responses.JSONResponse, response_model = list[MessageResponseModel],
description =
"""
Маршрут для получения всех сообщений в комментариях указанного чата указанного корневого (Parent) сообщения с полнотекстовым поиском по тексту сообщения (По указанному в параметрах сервера количеству записей за раз (50)).
""")
async def search_comments_in_chat(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    message_text: str = fastapi.Query(),
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.search_comments_in_chat(offset_multiplier, message_text, selected_chat, selected_message, current_user, db)

@messages_router.post("/chats/id/{chat_id}/messages/id/{message_id}/read", response_class = fastapi.responses.JSONResponse,
description =
"""
Маршрут для отправки отметки о прочтении чужого сообщения в групповом и приватном чате.
""")
async def mark_message_as_read(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.mark_message_as_read(selected_chat, selected_message, current_user, redis_client, db)


@messages_router.post("/chats/id/{chat_id}/messages/read-all", response_class = fastapi.responses.Response,
description =
"""
Маршрут для отметки всех непрочитанных корневых сообщений в указанном чате как прочитанных.
"""
)
async def mark_chat_messages_as_read(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    redis_client: RedisClient = fastapi.Depends(get_redis_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.Response:

    return await service.mark_chat_messages_as_read(selected_chat, current_user, redis_client, db)


@messages_router.get("/chats/id/{chat_id}/messages/last", response_class = fastapi.responses.JSONResponse, response_model = LastMessageResponseModel,
description =
"""
Маршрут для получения последнего сообщения (Корневого) в указанном чате.
""")
async def get_chat_last_message(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    current_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_chat_last_message(selected_chat, current_user, db)
