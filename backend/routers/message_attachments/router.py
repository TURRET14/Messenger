import fastapi
import sqlalchemy.ext.asyncio

from backend.storage import *
from backend.routers.message_attachments.response_models import (MessageAttachmentResponseModel)
from backend.routers.message_attachments import service
import backend.routers.dependencies

message_attachments_router = fastapi.APIRouter()

@message_attachments_router.get("/chats/id/{chat_id}/messages/id/{message_id}/attachments", response_class = fastapi.responses.JSONResponse, response_model = list[MessageAttachmentResponseModel],
description =
"""
Маршрут получения всех записей вложений у указанному сообщению в указанном чате.
""")
async def get_message_attachments_list(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await service.get_message_attachments_list(selected_chat, selected_message, selected_user, db)


@message_attachments_router.get("chats/id/{chat_id}/messages/id/{message_id}/attachments/id/{attachment_id}", response_class = fastapi.responses.StreamingResponse,
description =
"""
Маршрут для получения файла указанного вложения к указанному сообщению в указанном чате.
""")
async def get_message_attachment_file(
    selected_chat: Chat = fastapi.Depends(backend.routers.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.routers.dependencies.get_message_by_path_id),
    selected_attachment: MessageAttachment = fastapi.Depends(backend.routers.dependencies.get_message_attachment_by_id),
    selected_user: User = fastapi.Depends(backend.routers.dependencies.get_session_user),
    minio_client: MinioClient = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(database.get_db)) -> fastapi.responses.StreamingResponse:

    return await service.get_message_attachment_file(selected_chat, selected_message, selected_attachment, selected_user, minio_client, db)