import fastapi
import fastapi.encoders
import redis
import sqlalchemy.orm
import minio
import pathlib
import uuid
import io
import asyncio
import json
from typing import Sequence

from backend.storage import *
from models import *
import backend.routers.return_details
import backend.routers.dependencies
import backend.routers.parameters
import utils
import backend.routers.users.utils


async def get_all_chats(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    subquery: sqlalchemy.Subquery = (sqlalchemy.select(Message.chat_id.label("chat_id"),
    sqlalchemy.func.max(Message.date_and_time_sent).label("date_and_time_sent"))
    .select_from(Message)
    .group_by(Message.chat_id)
    .subquery())

    chats_list: Sequence[sqlalchemy.RowMapping] = (db.execute(
    sqlalchemy.select(
    Chat.id,
    Chat.chat_kind,
    sqlalchemy.func.coalesce(Chat.name, db.execute(sqlalchemy.select(User.username).select_from(ChatUser).where(sqlalchemy.and_(ChatUser.chat_id == Chat.id, ChatUser.chat_user_id != selected_user.id)).join(User, User.id == ChatUser.chat_user_id))),
    Chat.owner_user_id,
    Chat.date_and_time_created,
    Chat.is_read_only)
    .select_from(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_user_id == selected_user.id, ChatUser.is_active == True))
    .join(Chat, Chat.id == ChatUser.chat_id)
    .join(subquery, subquery.c.chat_id == Chat.id)
    .order_by(subquery.c.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chats_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    selected_chat: ChatResponseModel = ChatResponseModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = selected_chat.name,
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_read_only = selected_chat.is_read_only
    )

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_chat), status_code = fastapi.status.HTTP_200_OK)



async def get_chat_members(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    users_list: Sequence[sqlalchemy.RowMapping] = (db.execute(sqlalchemy.select(
    User.id,
    ChatUser.chat_id,
    User.username,
    User.name,
    User.surname,
    User.second_name,
    ChatUser.date_and_time_added,
    ChatUser.chat_role)
    .select_from(ChatUser)
    .where(sqlalchemy.and_(ChatUser.chat_id == selected_chat.id, ChatUser.is_active == True))
    .join(User, User.id == ChatUser.chat_user_id)
    .order_by(Chat.id)
    .offset(offset_multiplier * backend.routers.parameters.number_of_table_entries_in_selection)
    .limit(backend.routers.parameters.number_of_table_entries_in_selection))
    .mappings().all())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_last_message(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    last_message: Sequence[sqlalchemy.RowMapping] = db.execute(sqlalchemy.select(
    Message.id,
    Message.chat_id,
    Message.date_and_time_sent,
    Message.date_and_time_edited,
    Message.message_text,
    User.id.label("sender_id"),
    User.username.label("sender_username"),
    User.name.label("sender_name"),
    User.surname.label("sender_surname"),
    User.second_name.label("sender_second_name"))
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

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.group:
        if not selected_chat.avatar_photo_path:
            return fastapi.responses.FileResponse(backend.routers.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)
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
            return fastapi.responses.FileResponse(backend.routers.parameters.default_avatar_path, status_code = fastapi.status.HTTP_200_OK)
        else:
            file = minio_client.get_object("users:avatars", avatar_photo_path)
            file_stat = minio_client.stat_object("users:avatars", avatar_photo_path)

            return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type,
            headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK)


async def create_or_join_private_chat(
    friend_user: User,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if backend.routers.users.utils.get_user_block(selected_user, friend_user, db) or backend.routers.users.utils.get_user_block(friend_user, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    private_chat: Chat = await utils.get_users_private_chat(selected_user, friend_user, db)

    if not private_chat:
        new_chat: Chat = Chat(
        chat_kind = ChatKind.private,
        date_and_time_created = datetime.datetime.now(datetime.timezone.utc))

        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)

        first_chat_user: ChatUser = ChatUser(
        chat_id = new_chat.id,
        chat_user_id = selected_user.id,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
        is_active = True)

        second_chat_user: ChatUser = ChatUser(
        chat_id = new_chat.id,
        chat_user_id = friend_user.id,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
        is_active = True)

        db.add(first_chat_user)
        db.add(second_chat_user)
        db.commit()

        asyncio.run(redis_client.publish("chats_post", json.dumps(ChatWithReceiversModel(chat = new_chat, receivers = [selected_user, friend_user], is_avatar_changed = False))))

        return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)
    else:
        membership: ChatUser = await utils.get_user_chat_membership(private_chat, selected_user, db)
        if not membership.is_active:
            membership.is_active = True
            private_chat.is_read_only = False
            db.commit()

            asyncio.run(redis_client.publish("chats_post", json.dumps(ChatWithReceiversModel(chat = private_chat, receivers = [selected_user], is_avatar_changed = False))))

            return fastapi.responses.JSONResponse({"id": membership.id}, status_code = fastapi.status.HTTP_200_OK)
        else:
            raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.CONFLICT_ERROR)




async def create_group_chat(
    data: GroupChatModel,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    new_chat: Chat = Chat(
    chat_kind = ChatKind.group,
    owner_user_id = selected_user.id,
    name = data.name,
    date_and_time_created = datetime.datetime.now(datetime.timezone.utc))
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    membership: ChatUser = ChatUser(
    chat_id = new_chat.id,
    chat_user_id = selected_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.owner,
    is_active = True)

    db.add(membership)
    db.commit()
    db.refresh(membership)

    asyncio.run(redis_client.publish("chats_post", json.dumps(ChatWithReceiversModel(chat = new_chat, receivers = [selected_user], is_avatar_changed = True))))

    return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_avatar(
    selected_chat: Chat,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: minio.Minio,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if file.content_type not in backend.routers.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_TYPE_NOT_ALLOWED_ERROR)

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.routers.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_TYPE_NOT_ALLOWED_ERROR)

    if file.size > backend.routers.parameters.max_avatar_size_bytes:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.IMAGE_SIZE_TOO_LARGE_ERROR)

    #MinIO - Загрузка аватара
    minio_file_name: str = f"chats/{selected_chat.id}/{uuid.uuid4().hex.upper()}{image_extension}"
    file_content = await file.read()
    minio_client.put_object("chats:avatars", minio_file_name, io.BytesIO(file_content), len(file_content), file.content_type)

    # MinIO - Удаление старого аватара
    if selected_chat.avatar_photo_path is not None:
        minio_client.remove_object("chats:avatars", selected_chat.avatar_photo_path)

    selected_chat.avatar_photo_path = minio_file_name
    db.commit()

    asyncio.run(redis_client.publish("chats_put", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = list(db.execute(sqlalchemy.select(User).select_from(ChatUser).where(ChatUser.chat_id == selected_chat.id).join(User, User.id == ChatUser.chat_user_id)).scalars().all()), is_avatar_changed = False))))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code=fastapi.status.HTTP_200_OK)


async def update_chat_name(
    selected_chat: Chat,
    data: GroupChatModel,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    selected_chat.name = data.name
    db.commit()

    asyncio.run(redis_client.publish("chats_put", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = list(db.execute(sqlalchemy.select(User).select_from(ChatUser).where(ChatUser.chat_id == selected_chat.id).join(User, User.id == ChatUser.chat_user_id)).scalars().all()), is_avatar_changed = False))))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def update_chat_owner(
    selected_chat: Chat,
    new_owner_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not selected_chat.chat_kind == ChatKind.group:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    old_owner_membership: ChatUser = await utils.get_chat_user_membership(selected_chat, selected_user, db)
    if not old_owner_membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)
    
    new_owner_membership: ChatUser = await utils.get_chat_user_membership(selected_chat, new_owner_user, db)
    if not new_owner_membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)


    selected_chat.owner_user_id = new_owner_user.id
    old_owner_membership.chat_role = ChatRole.user
    new_owner_membership.chat_role = ChatRole.owner
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def add_chat_admin(
    selected_chat: Chat,
    new_admin_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_chat.chat_kind not in [ChatKind.group, ChatKind.community]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_user.id == new_admin_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_409_CONFLICT, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    membership: ChatUser = await utils.get_chat_user_membership(selected_chat, new_admin_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)
    membership.chat_role = ChatRole.admin
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)

async def delete_chat_admin(
    selected_chat: Chat,
    admin_user: User,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_chat.chat_kind not in [ChatKind.group, ChatKind.community]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    membership: ChatUser = await utils.get_chat_user_membership(selected_chat, admin_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    membership.chat_role = ChatRole.user
    db.commit()

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def add_chat_user(
    selected_chat: Chat,
    new_user: User,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_chat.chat_kind not in [ChatKind.group, ChatKind.community]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if not await utils.get_users_friendship(selected_user, new_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if await utils.get_chat_user_membership(selected_chat, new_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    membership: ChatUser = ChatUser(
    chat_id = selected_chat.id,
    chat_user_id = new_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.user,
    is_active = True)

    db.add(membership)
    db.commit()

    asyncio.run(redis_client.publish("chats_post", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = [new_user], is_avatar_changed = False))))

    return fastapi.responses.JSONResponse({"id": membership.id}, status_code = fastapi.status.HTTP_200_OK)


async def delete_chat_user(
    selected_chat: Chat,
    chat_user: User,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_chat.chat_kind not in [ChatKind.group, ChatKind.community]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner_or_admin(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_user.id == chat_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    membership: ChatUser = await utils.get_chat_user_membership(selected_chat, chat_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    db.delete(membership)
    db.commit()

    asyncio.run(redis_client.publish("chats_delete", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = [chat_user], is_avatar_changed = False))))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code=fastapi.status.HTTP_200_OK)


async def leave_chat(
    selected_chat: Chat,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    membership: ChatUser = await utils.get_chat_user_membership(selected_chat, selected_user, db)
    if not membership:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.chat_kind == ChatKind.private:
        membership.is_active = False
        selected_chat.is_read_only = True
    else:
        db.delete(membership)

    db.commit()

    asyncio.run(redis_client.publish("chats_delete", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = [selected_user], is_avatar_changed = False))))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def delete_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: minio.Minio,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if selected_chat.chat_kind not in [ChatKind.group, ChatKind.community]:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if not await utils.is_chat_user_owner(selected_chat, selected_user):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_chat.avatar_photo_path:
        minio_client.remove_object("groups:avatars", selected_chat.avatar_photo_path)

    db.delete(selected_chat)
    db.commit()

    asyncio.run(redis_client.publish("chats_delete", json.dumps(ChatWithReceiversModel(chat = selected_chat, receivers = list(db.execute(sqlalchemy.select(User).select_from(ChatUser).where(ChatUser.chat_id == selected_chat.id).join(User, User.id == ChatUser.chat_user_id)).scalars().all()), is_avatar_changed = False))))

    return fastapi.responses.JSONResponse(backend.routers.return_details.SUCCESS_RETURN_MESSAGE, status_code = fastapi.status.HTTP_200_OK)


async def create_community(
    data: GroupChatModel,
    selected_user: User,
    redis_client: redis.Redis,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    new_chat: Chat = Chat(
    chat_kind = ChatKind.community,
    owner_user_id = selected_user.id,
    name = data.name,
    date_and_time_created = datetime.datetime.now(datetime.timezone.utc))
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    membership: ChatUser = ChatUser(
    chat_id = new_chat.id,
    chat_user_id = selected_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.owner,
    is_active = True)

    db.add(membership)
    db.commit()
    db.refresh(membership)

    asyncio.run(redis_client.publish("chats_post", json.dumps(ChatWithReceiversModel(chat = new_chat, receivers = [selected_user], is_avatar_changed = True))))

    return fastapi.responses.JSONResponse({"id": new_chat.id}, status_code = fastapi.status.HTTP_200_OK)


async def get_discussion_by_community_message_id(
    selected_message: Message,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

    if not await utils.get_chat_user_membership(selected_chat, selected_user, db):
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_403_FORBIDDEN, detail = backend.routers.return_details.FORBIDDEN_ERROR)

    if selected_message.chat_id != selected_chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    if selected_chat.chat_kind != ChatKind.community:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = backend.routers.return_details.BAD_REQUEST_ERROR)

    message_discussion: Chat = (db.execute(sqlalchemy.select(
    Chat.id,
    Chat.chat_kind,
    Chat.name,
    Chat.owner_user_id,
    Chat.date_and_time_created,
    Chat.is_read_only)
    .select_from(Chat)
    .where(Chat.discussion_message_id == selected_message.id))
    .scalars().first())

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(message_discussion), status_code = fastapi.status.HTTP_200_OK)