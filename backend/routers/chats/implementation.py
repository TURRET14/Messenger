import datetime

import fastapi
import sqlalchemy.orm
import minio
import pathlib
import uuid
import io

import backend.dependencies
import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.minio_handler
import backend.storage.database
import backend.storage.redis_handler
import backend.parameters


async def get_all_user_chats(
    offset_multiplier: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")


    subquery = sqlalchemy.select(backend.storage.database.Message.chat_id.label("chat_id"),
    sqlalchemy.func.max(backend.storage.database.Message.date_and_time_sent).label("date_and_time_sent")).select_from(backend.storage.database.Message).group_by(backend.storage.database.Message.chat_id).subquery()

    chats_list = db.execute(sqlalchemy.select(
    backend.storage.database.Chat.id,
    backend.storage.database.Chat.is_group_chat,
    backend.storage.database.Chat.name,
    backend.storage.database.Chat.owner_user_id,
    backend.storage.database.Chat.date_and_time_created)
    .select_from(backend.storage.database.ChatUser)
    .where(backend.storage.database.ChatUser.chat_user_id == selected_user.id)
    .join(backend.storage.database.Chat, backend.storage.database.Chat.id == backend.storage.database.ChatUser.chat_id)
    .join(subquery, subquery.c.chat_id == backend.storage.database.Chat.id)
    .order_by(subquery.c.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).all()

    return fastapi.responses.JSONResponse(chats_list, status_code = fastapi.status.HTTP_200_OK)


async def get_chat(
    chat_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(
    backend.storage.database.Chat.id,
    backend.storage.database.Chat.is_group_chat,
    backend.storage.database.Chat.name,
    backend.storage.database.Chat.owner_user_id,
    backend.storage.database.Chat.date_and_time_created)
    .select_from(backend.storage.database.ChatUser)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()
    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
        detail="USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    return fastapi.responses.JSONResponse(chat, status_code = fastapi.status.HTTP_200_OK)




async def get_chat_users(
    chat_id: int,
    offset_multiplier: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "CHAT_DOES_NOT_EXIST_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id))).first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED,
        detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    users_list = db.execute(sqlalchemy.select(
    backend.storage.database.User.id,
    backend.storage.database.User.username,
    backend.storage.database.User.name,
    backend.storage.database.User.surname,
    backend.storage.database.User.second_name,
    backend.storage.database.ChatUser.is_user_admin)
    .select_from(backend.storage.database.ChatUser)
    .where(backend.storage.database.ChatUser.chat_id == chat_id)
    .join(backend.storage.database.User, backend.storage.database.User.id == backend.storage.database.ChatUser.chat_user_id)
    .order_by(backend.storage.database.Chat.id)
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all()

    return fastapi.responses.JSONResponse(users_list, status_code = fastapi.status.HTTP_200_OK)


async def get_chat_last_message(
    chat_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "CHAT_DOES_NOT_EXIST_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id))).first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED,
        detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    message = db.execute(sqlalchemy.select(
    backend.storage.database.Message.id,
    backend.storage.database.Message.chat_id,
    backend.storage.database.Message.date_and_time_sent,
    backend.storage.database.Message.message_text,
    backend.storage.database.User.username,
    backend.storage.database.User.name,
    backend.storage.database.User.surname,
    backend.storage.database.User.second_name)
    .select_from(backend.storage.database.Message)
    .where(backend.storage.database.Message.chat_id == chat_id)
    .join(backend.storage.database.User, backend.storage.database.User.id == backend.storage.database.Message.sender_user_id)
    .order_by(backend.storage.database.Message.date_and_time_sent.desc())
    .limit(1)).first()

    return fastapi.responses.JSONResponse(message, status_code = fastapi.status.HTTP_200_OK)


async def get_chat_avatar(
    chat_id: int,
    selected_user: backend.storage.database.User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.StreamingResponse | fastapi.responses.FileResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).scalars().first()
    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
        detail="USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    if chat.is_group_chat:
        if not chat.avatar_photo_path:
            return fastapi.responses.FileResponse("/images/avatar.png", status_code = fastapi.status.HTTP_200_OK)
        else:
            file = minio_client.get_object("groups:avatars", chat.avatar_photo_path)
            file_stat = minio_client.stat_object("groups:avatars", chat.avatar_photo_path)

            return fastapi.responses.StreamingResponse(file.stream(), media_type=file_stat.content_type,
            headers={"Content-Disposition": "inline"}, status_code=fastapi.status.HTTP_200_OK)

    else:
        avatar_photo_path: str = (db.execute(sqlalchemy.select(backend.storage.database.User.avatar_photo_path)
        .select_from(backend.storage.database.ChatUser)
        .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
        backend.storage.database.ChatUser.chat_user_id != selected_user.id))).scalar())
        if not avatar_photo_path:
            return fastapi.responses.FileResponse("/images/avatar.png", status_code=fastapi.status.HTTP_200_OK)
        else:
            file = minio_client.get_object("users:avatars", chat.avatar_photo_path)
            file_stat = minio_client.stat_object("users:avatars", chat.avatar_photo_path)

            return fastapi.responses.StreamingResponse(file.stream(), media_type=file_stat.content_type,
            headers={"Content-Disposition": "inline"}, status_code=fastapi.status.HTTP_200_OK)


async def create_private_chat(
    data: backend.models.pydantic_request_models.IDModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    friendship: backend.storage.database.UserFriend = db.execute(sqlalchemy.select(backend.storage.database.UserFriend)
    .where(sqlalchemy.or_(sqlalchemy.and_(backend.storage.database.UserFriend.user_id == selected_user.id,
    backend.storage.database.UserFriend.friend_user_id == data.id),
    sqlalchemy.and_(backend.storage.database.UserFriend.user_id == data.id,
    backend.storage.database.UserFriend.friend_user_id == selected_user.id)))).scalars().first()

    if not friendship:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "SELECTED_USER_IS_NOT_A_FRIEND_ERROR")

    # left = sqlalchemy.select(backend.storage.database.ChatUser.chat_id.label("chat_id_left")).select_from(backend.storage.database.ChatUser).where(backend.storage.database.ChatUser.chat_user_id == current_user.id).join(backend.storage.database.Chat).where(backend.storage.database.Chat.is_group_chat == False).subquery()
    # right = sqlalchemy.select(backend.storage.database.ChatUser.chat_id.label("chat_id_right")).select_from(backend.storage.database.ChatUser).where(backend.storage.database.ChatUser.chat_user_id == data.id).join(backend.storage.database.Chat).where(backend.storage.database.Chat.is_group_chat == False).subquery()
    #
    # if db.execute(sqlalchemy.select(left.c.chat_id_left).select_from(left.join(right, left.c.chat_id_left == right.c.chat_id_right))).scalars().first():
    #     raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = "CHAT_ALREADY_EXISTS")

    if db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.friendship_id == friendship)).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_409_CONFLICT, detail="CHAT_ALREADY_EXISTS")


    new_chat: backend.storage.database.Chat = backend.storage.database.Chat(is_group_chat = False,
    date_and_time_created = datetime.datetime.now(datetime.timezone.utc),
    friendship_id = friendship.id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    first_chat_user: backend.storage.database.ChatUser = backend.storage.database.ChatUser(
    chat_id = new_chat.id,
    chat_user_id = selected_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    second_chat_user: backend.storage.database.ChatUser = backend.storage.database.ChatUser(
    chat_id=new_chat.id,
    chat_user_id=data.id,
    date_and_time_added=datetime.datetime.now(datetime.timezone.utc))

    db.add(first_chat_user)
    db.add(second_chat_user)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)


async def create_group_chat(
    data: backend.models.pydantic_request_models.GroupChatModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    new_chat: backend.storage.database.Chat = backend.storage.database.Chat(is_group_chat = True, owner_user_id = selected_user.id, name = data.name, date_and_time_created = datetime.datetime.now(datetime.timezone.utc))
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_avatar(
    chat_id: int,
    file: fastapi.UploadFile,
    selected_user: backend.storage.database.User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id and db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id
    ))).scalars().first().is_user_admin == False:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "PERMISSION_DENIED_ERROR")

    if file.content_type not in backend.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "IMAGE_TYPE_NOT_ALLOWED_ERROR")

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "IMAGE_TYPE_NOT_ALLOWED_ERROR")

    if file.size > backend.parameters.max_avatar_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="IMAGE_SIZE_TOO_LARGE_ERROR")

    #MinIO - Загрузка аватара
    minio_file_name: str = f"chats/{chat.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("chats:avatars", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)

    # MinIO - Удаление старого аватара
    if chat.avatar_photo_path is not None:
        minio_client.remove_object("chats:avatars", chat.avatar_photo_path)

    chat.avatar_photo_path = minio_file_name
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def update_chat_name(
    chat_id: int,
    data: backend.models.pydantic_request_models.GroupChatModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id and db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id
    ))).scalars().first().is_user_admin == False:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "PERMISSION_DENIED_ERROR")

    chat.name = data.name
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_owner(
    chat_id: int,
    data: backend.models.pydantic_request_models.IDModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat).where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="PERMISSION_DENIED_ERROR")
    membership: backend.storage.database.ChatUser = db.execute(sqlalchemy.select(backend.storage.database.ChatUser).
    where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == data.id))).scalars().first()
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    chat.owner_user_id = data.id
    membership.is_user_admin = None
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def add_chat_admin(
    chat_id: int,
    data: backend.models.pydantic_request_models.IDModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="PERMISSION_DENIED_ERROR")

    membership: backend.storage.database.ChatUser = db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == data.id))).scalars().first()

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    membership.is_user_admin = True
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)

async def delete_chat_admin(
    chat_id: int,
    admin_user_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()
    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="PERMISSION_DENIED_ERROR")

    membership: backend.storage.database.ChatUser = db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == admin_user_id))).scalars().first()

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    membership.is_user_admin = False
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def add_chat_user(
    chat_id: int,
    data: backend.models.pydantic_request_models.IDModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.id == data.id)).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id and db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id
    ))).scalars().first().is_user_admin == False:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "PERMISSION_DENIED_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == data.id))).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USER_ALREADY_IN_CHAT_ERROR")

    membership: backend.storage.database.ChatUser = backend.storage.database.ChatUser(
    chat_id = chat.id,
    chat_user_id = data.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    is_user_admin = False)

    db.add(membership)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def delete_chat_user(
    chat_id: int,
    chat_user_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    if not db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.id == chat_user_id)).scalars().first():
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if chat.owner_user_id != selected_user.id and db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat.id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id
    ))).scalars().first().is_user_admin == False:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "PERMISSION_DENIED_ERROR")

    membership: backend.storage.database.ChatUser = db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == chat_user_id))).scalars().first()

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    if selected_user.id == chat_user_id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "CANT_DELETE_YOURSELF_ERROR")

    if chat.owner_user_id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "CANT_DELETE_OWNER_ERROR")

    if membership.is_user_admin:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED,detail="CANT_DELETE_ADMIN_ERROR")

    db.delete(membership)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def leave_chat(
    chat_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND,detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    membership: backend.storage.database.ChatUser = db.execute(sqlalchemy.select(backend.storage.database.ChatUser)
    .where(sqlalchemy.and_(backend.storage.database.ChatUser.chat_id == chat_id,
    backend.storage.database.ChatUser.chat_user_id == selected_user.id))).scalars().first()

    if not membership:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="USER_IS_NOT_A_MEMBER_OF_SELECTED_CHAT_ERROR")

    db.delete(membership)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)


async def delete_chat(
    chat_id: int,
    selected_user: backend.storage.database.User,
    minio_client: minio.Minio,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    chat: backend.storage.database.Chat = db.execute(sqlalchemy.select(backend.storage.database.Chat)
    .where(backend.storage.database.Chat.id == chat_id)).scalars().first()

    if not chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND,detail="CHAT_DOES_NOT_EXIST_ERROR")

    if not chat.is_group_chat:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="NOT_POSSIBLE_IN_PRIVATE_CHAT_ERROR")

    if not chat.owner_user_id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="NOT_CHAT_OWNER_ERROR")

    if chat.avatar_photo_path:
        minio_client.remove_object("groups:avatars", chat.avatar_photo_path)

    db.delete(chat)
    db.commit()

    return fastapi.responses.JSONResponse({"STATUS": "SUCCESS"}, status_code=fastapi.status.HTTP_200_OK)