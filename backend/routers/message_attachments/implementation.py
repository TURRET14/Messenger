import fastapi
import fastapi.encoders
import sqlalchemy.orm
import minio
import pathlib
import uuid
import io


from backend.storage import *
from backend.return_details import *
import backend.dependencies
import backend.parameters
import backend.routers.utils


async def get_message_attachments_list(
    selected_chat: Chat,
    selected_message: Message,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    attachments_list: sqlalchemy.Sequence[FileAttachment] = db.execute(sqlalchemy.select(FileAttachment)
    .where(FileAttachment.message_id == selected_message.id)).scalars().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(attachments_list), status_code = fastapi.status.HTTP_200_OK)


async def get_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: FileAttachment,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.StreamingResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_message.chat_id != selected_chat.id or selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    file = minio_client.get_object("messages:attachments", selected_attachment.attachment_file_path)
    file_stat = minio_client.stat_object("messages:attachments", selected_attachment.attachment_file_path)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def add_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: minio.Minio = fastapi.Depends(minio_handler.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if file.size > backend.parameters.max_attachment_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_size_too_large_error)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    #MinIO - Загрузка аватара
    minio_file_name: str = f"messages/{selected_message.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("messages:attachments", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)


    new_attachment: FileAttachment = FileAttachment(
    message_id = selected_message.id,
    attachment_file_path = minio_file_name)
    db.commit()
    db.refresh(new_attachment)

    return fastapi.responses.JSONResponse({"id": new_attachment.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_message_attachment_file(
    selected_chat: Chat,
    selected_message: Message,
    selected_attachment: FileAttachment,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_message.chat_id != selected_chat.id or selected_attachment.message_id != selected_message.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    minio_client.remove_object("messages:attachments", selected_attachment.attachment_file_path)

    db.delete(selected_attachment)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)