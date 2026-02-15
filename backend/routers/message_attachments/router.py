import fastapi
import minio
import sqlalchemy.orm

from backend.storage import *
from models import *
from backend.return_details import *
import implementation
import backend.dependencies

message_attachments_router = fastapi.APIRouter()


@message_attachments_router.get("/chats/id/{chat_id}/messages/id/{message_id}/attachments", response_class = fastapi.responses.JSONResponse)
async def get_message_attachments_list(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await implementation.get_message_attachments_list(selected_chat, selected_message, selected_user, db)


@message_attachments_router.get("chats/id/{chat_id}/messages/id/{message_id}/attachments/id/{attachment_id}", response_class = fastapi.responses.JSONResponse)
async def get_message_attachment_file(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    selected_attachment: FileAttachment = fastapi.Depends(backend.dependencies.get_message_attachment_by_id),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.StreamingResponse:

    return await implementation.get_message_attachment_file(selected_chat, selected_message, selected_attachment, selected_user, minio_client, db)


@message_attachments_router.post("chats/id/{chat_id}/messages/id/{message_id}/attachments", response_class = fastapi.responses.JSONResponse)
async def add_message_attachment_file(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    file: fastapi.UploadFile = fastapi.File(),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await implementation.add_message_attachment_file(selected_chat, selected_message, file, selected_user, minio_client, db)


@message_attachments_router.post("chats/id/{chat_id}/messages/id/{message_id}/attachments/id/{attachment_id}", response_class=fastapi.responses.JSONResponse)
async def delete_message_attachment_file(
    selected_chat: Chat = fastapi.Depends(backend.dependencies.get_chat_by_path_id),
    selected_message: Message = fastapi.Depends(backend.dependencies.get_message_by_path_id),
    selected_attachment: FileAttachment = fastapi.Depends(backend.dependencies.get_message_attachment_by_id),
    selected_user: User = fastapi.Depends(backend.dependencies.get_session_user),
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    return await implementation.delete_message_attachment_file(selected_chat, selected_message, selected_attachment, selected_user, minio_client, db)