import fastapi
import fastapi.encoders
import sqlalchemy.orm
import minio
import pathlib
import uuid
import io
import datetime

from backend.storage import *
from models import *
from backend.return_details import *
import backend.dependencies
import backend.parameters
import backend.routers.utils


async def get_all_chats(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    subquery: sqlalchemy.Subquery = sqlalchemy.select(Message.chat_id.label("chat_id"),
    sqlalchemy.func.max(Message.date_and_time_sent).label("date_and_time_sent")).select_from(Message).group_by(Message.chat_id).subquery()

    chats_list: sqlalchemy.Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    Chat.id,
    Chat.chat_kind,
    Chat.name,
    Chat.owner_user_id,
    Chat.date_and_time_created)
    .select_from(ChatUser)
    .where(ChatUser.chat_user_id == selected_user.id)
    .join(Chat, Chat.id == ChatUser.chat_id)
    .join(subquery, subquery.c.chat_id == Chat.id)
    .order_by(subquery.c.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chats_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    selected_chat: dict = {
        "id": selected_chat.id,
        "is_group_chat": selected_chat.chat_kind,
        "name": selected_chat.name,
        "owner_user_id": selected_chat.owner_user_id,
        "date_and_time_created": selected_chat.date_and_time_created
    }

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_chat), status_code = fastapi.status.HTTP_200_OK)



async def get_chat_members(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    users_list: sqlalchemy.Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    User.id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    ChatUser.chat_role)
    .select_from(ChatUser)
    .where(ChatUser.chat_id == selected_chat.id)
    .join(User, User.id == ChatUser.chat_user_id)
    .order_by(Chat.id)
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).mappings().all()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_last_message(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    last_message: sqlalchemy.Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    Message.id,
    Message.chat_id,
    Message.date_and_time_sent,
    Message.message_text,
    User.username,
    User.name,
    User.surname,
    User.second_name)
    .select_from(Message)
    .where(Message.chat_id == selected_chat.id)
    .join(User, User.id == Message.sender_user_id)
    .order_by(Message.date_and_time_sent.desc())
    .limit(1)).mappings().first()

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(last_message), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_avatar(
    selected_chat: Chat,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    if not await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_chat.chat_kind == ChatKind.group:
        if not selected_chat.avatar_photo_path:
            return fastapi.responses.FileResponse(backend.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)
        else:
            file = minio_client.get_object("groups:avatars", selected_chat.avatar_photo_path)
            file_stat = minio_client.stat_object("groups:avatars", selected_chat.avatar_photo_path)

            return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type,
            headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)

    else:
        avatar_photo_path: str = (db.execute(sqlalchemy.select(User.avatar_photo_path)
        .select_from(ChatUser)
        .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id,
        ChatUser.chat_user_id != selected_user.id))).scalar())
        if not avatar_photo_path:
            return fastapi.responses.FileResponse(backend.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)
        else:
            file = minio_client.get_object("users:avatars", avatar_photo_path)
            file_stat = minio_client.stat_object("users:avatars", avatar_photo_path)

            return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type,
            headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def create_private_chat(
    friend_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    friendship: UserFriend = await backend.routers.utils.get_users_friendship(selected_user, friend_user, db)
    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if db.execute(sqlalchemy.select(Chat).where(Chat.friendship_id == friendship.id)).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.conflict_error)


    new_chat: Chat = Chat(
    is_group_chat = False,
    date_and_time_created = datetime.datetime.now(datetime.timezone.utc),
    friendship_id = friendship.id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    first_chat_user: ChatUser = ChatUser(
    chat_id = new_chat.id,
    chat_user_id = selected_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    second_chat_user: ChatUser = ChatUser(
    chat_id = new_chat.id,
    chat_user_id = friend_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    db.add(first_chat_user)
    db.add(second_chat_user)
    db.commit()

    return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)


async def create_group_chat(
    data: GroupChatModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    new_chat: Chat = Chat(is_group_chat = True, owner_user_id = selected_user.id, name = data.name, date_and_time_created = datetime.datetime.now(datetime.timezone.utc))
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_avatar(
    selected_chat: Chat,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if file.content_type not in backend.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_type_not_allowed_error)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_type_not_allowed_error)

    if file.size > backend.parameters.max_avatar_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.image_size_too_large_error)

    #MinIO - Загрузка аватара
    minio_file_name: str = f"chats/{selected_chat.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("chats:avatars", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)

    # MinIO - Удаление старого аватара
    if selected_chat.avatar_photo_path is not None:
        minio_client.remove_object("chats:avatars", selected_chat.avatar_photo_path)

    selected_chat.avatar_photo_path = minio_file_name
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code=fastapi.status.HTTP_200_OK)


async def update_chat_name(
    selected_chat: Chat,
    data: GroupChatModel,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    selected_chat.name = data.name
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_owner(
    selected_chat: Chat,
    new_owner_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    old_owner_membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db)
    if not old_owner_membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)
    
    new_owner_membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, new_owner_user, db)
    if not new_owner_membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)


    selected_chat.owner_user_id = new_owner_user.id
    old_owner_membership.chat_role = ChatRole.user
    new_owner_membership.chat_role = ChatRole.owner
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def add_chat_admin(
    selected_chat: Chat,
    new_admin_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_user.id == new_admin_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = ExceptionDetails.bad_request_error)

    membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, new_admin_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)
    membership.chat_role = ChatRole.admin
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)

async def delete_chat_admin(
    selected_chat: Chat,
    admin_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, admin_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    membership.chat_role = ChatRole.user
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)


async def add_chat_user(
    selected_chat: Chat,
    new_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if not await backend.routers.utils.get_users_friendship(selected_user, new_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if await backend.routers.utils.get_chat_user_membership(selected_chat, new_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    membership: ChatUser = ChatUser(
    chat_id = selected_chat.id,
    chat_user_id = new_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.user)

    db.add(membership)
    db.commit()

    return fastapi.responses.JSONResponse({"id": membership.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_chat_user(
    selected_chat: Chat,
    chat_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_user.id == chat_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, chat_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    db.delete(membership)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code=fastapi.status.HTTP_200_OK)


async def leave_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=ExceptionDetails.bad_request_error)

    membership: ChatUser = await backend.routers.utils.get_chat_user_membership(selected_chat, selected_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    db.delete(membership)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code=fastapi.status.HTTP_200_OK)


async def delete_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = ExceptionDetails.bad_request_error)

    if not await backend.routers.utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = ExceptionDetails.forbidden_error)

    if selected_chat.avatar_photo_path:
        minio_client.remove_object("groups:avatars", selected_chat.avatar_photo_path)

    db.delete(selected_chat)
    db.commit()

    return fastapi.responses.JSONResponse(success_return_message, status_code = fastapi.status.HTTP_200_OK)