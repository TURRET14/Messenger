import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence
import datetime

from backend.routers.chats import minio_deletion_service
from backend.routers.common_models import IDModel
from backend.storage import *
from backend.routers.chats.request_models import (ChatNameRequestModel)
from backend.routers.chats.response_models import (ChatResponseModel, ChatMembershipResponseModel)
import backend.routers.errors
import backend.routers.dependencies
import backend.routers.parameters
import backend.routers.users.utils
import backend.routers.messages.utils
from backend.routers.chats.validation import validators
import backend.routers.common_validators.validators as common_validators
import backend.routers.users.service


async def get_all_chats(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    subquery_chat_last_message_datetime: sqlalchemy.Subquery = (sqlalchemy.select(Message.chat_id.label("chat_id"),
    sqlalchemy.func.max(Message.date_and_time_sent).label("date_and_time_sent"))
    .select_from(Message)
    .group_by(Message.chat_id)
    .subquery())

    chats_list_raw: Sequence[tuple[Chat, str]] = ((await db.execute(
    sqlalchemy.select(
    Chat,
    sqlalchemy.func.coalesce(Chat.name, sqlalchemy.select(sqlalchemy.func.concat_ws(" ", User.name, User.surname, User.second_name)).select_from(ChatMembership).where(sqlalchemy.and_(ChatMembership.chat_id == Chat.id, ChatMembership.chat_user_id != selected_user.id)).join(User, User.id == ChatMembership.chat_user_id).limit(1).scalar_subquery()).label("chat_name"))
    .select_from(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_user_id == selected_user.id))
    .join(Chat, Chat.id == ChatMembership.chat_id)
    .join(subquery_chat_last_message_datetime, subquery_chat_last_message_datetime.c.chat_id == Chat.id)
    .order_by(subquery_chat_last_message_datetime.c.date_and_time_sent.desc())
    .offset(offset_multiplier * backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .tuples().all())

    chats_list: list[ChatResponseModel] = list()

    for chat, chat_name in chats_list_raw:
        chats_list.append(ChatResponseModel(
        id = chat.id,
        chat_kind = chat.chat_kind,
        name = chat_name,
        owner_user_id = chat.owner_user_id,
        date_and_time_created = chat.date_and_time_created))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chats_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    chat_name: str = await validators.validate_get_chat(selected_chat, selected_user, db)

    selected_chat: ChatResponseModel = ChatResponseModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = chat_name,
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_chat), status_code = fastapi.status.HTTP_200_OK)



async def get_chat_members(
    offset_multiplier: int,
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)

    membership_list_raw: Sequence[ChatMembership] = ((await db.execute(
    sqlalchemy.select(ChatMembership)
    .select_from(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_id == selected_chat.id))
    .join(User, User.id == ChatMembership.chat_user_id)
    .order_by(User.id)
    .offset(offset_multiplier * backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .scalars().all())

    memberships_list: list[ChatMembershipResponseModel] = list()

    for membership in membership_list_raw:
        memberships_list.append(ChatMembershipResponseModel(
        id = membership.id,
        chat_id = membership.chat_id,
        chat_user_id = membership.chat_user_id,
        date_and_time_added = membership.date_and_time_added,
        chat_role = membership.chat_role))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(memberships_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_avatar(
    selected_chat: Chat,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.StreamingResponse:

    avatar_photo_path: str = await validators.validate_get_chat_avatar(selected_chat, selected_user, db)

    file = await minio_client.get_file(MinioBucket.chats_avatars, avatar_photo_path)
    file_stat = await minio_client.get_file_stat(MinioBucket.chats_avatars, avatar_photo_path)

    background_tasks = fastapi.BackgroundTasks()
    background_tasks.add_task(minio_client.close_file_stream, file)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK, background = background_tasks)


async def create_private_chat(
    other_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_create_private_chat(selected_user, other_user, db)

    async with db.begin():
        new_chat: Chat = Chat(
        chat_kind = ChatKind.PRIVATE,
        date_and_time_created = datetime.datetime.now(datetime.timezone.utc))

        db.add(new_chat)
        await db.flush()
        await db.refresh(new_chat)

        first_chat_user: ChatMembership = ChatMembership(
        chat_id = new_chat.id,
        chat_user_id = selected_user.id,
        chat_role = ChatRole.USER,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

        second_chat_user: ChatMembership = ChatMembership(
        chat_id = new_chat.id,
        chat_user_id = other_user.id,
        chat_role = ChatRole.USER,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

        db.add(first_chat_user)
        db.add(second_chat_user)

    return fastapi.responses.JSONResponse(IDModel(id = new_chat.id), status_code = fastapi.status.HTTP_201_CREATED)


async def create_group_chat(
    data: ChatNameRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    async with db.begin():
        new_chat: Chat = Chat(
        chat_kind = ChatKind.GROUP,
        owner_user_id = selected_user.id,
        name = data.name,
        date_and_time_created = datetime.datetime.now(datetime.timezone.utc))

        db.add(new_chat)
        await db.flush()
        await db.refresh(new_chat)

        membership: ChatMembership = ChatMembership(
        chat_id = new_chat.id,
        chat_user_id = selected_user.id,
        chat_role = ChatRole.OWNER,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

        db.add(membership)

    return fastapi.responses.JSONResponse(IDModel(id = new_chat.id), status_code = fastapi.status.HTTP_201_CREATED)


async def update_chat_avatar(
    selected_chat: Chat,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_avatar_or_name(selected_chat, selected_user, db)

    old_avatar_path: str | None = selected_chat.avatar_photo_path
    new_avatar_photo_path: str = await minio_client.put_file(MinioBucket.chats_avatars, file)
    try:
        selected_chat.avatar_photo_path = new_avatar_photo_path
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await minio_client.delete_file(MinioBucket.chats_avatars, new_avatar_photo_path)

        raise

    if old_avatar_path:
        await minio_client.delete_file(MinioBucket.chats_avatars, old_avatar_path)

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_chat_name(
    selected_chat: Chat,
    data: ChatNameRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_avatar_or_name(selected_chat, selected_user, db)

    selected_chat.name = data.name
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_chat_owner(
    selected_chat: Chat,
    new_owner_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    old_owner_membership: ChatMembership = await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    
    new_owner_membership: ChatMembership = await validators.validate_update_chat_owner_and_add_admin(selected_chat, selected_user, new_owner_user, db)

    async with db.begin():
        selected_chat.owner_user_id = new_owner_user.id
        old_owner_membership.chat_role = ChatRole.USER
        new_owner_membership.chat_role = ChatRole.OWNER

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def add_chat_admin(
    selected_chat: Chat,
    new_admin_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    new_admin_membership: ChatMembership = await validators.validate_update_chat_owner_and_add_admin(selected_chat, selected_user, new_admin_user, db)

    new_admin_membership.chat_role = ChatRole.ADMIN
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)

async def delete_chat_admin(
    selected_chat: Chat,
    admin_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    admin_membership: ChatMembership = await validators.validate_delete_chat_admin(selected_chat, selected_user, admin_user, db)

    admin_membership.chat_role = ChatRole.USER
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def add_chat_user(
    selected_chat: Chat,
    new_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_add_user(selected_chat, selected_user, new_user, db)

    membership: ChatMembership = ChatMembership(
    chat_id = selected_chat.id,
    chat_user_id = new_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.USER)

    db.add(membership)
    await db.commit()

    return fastapi.responses.JSONResponse(IDModel(id = membership.id), status_code = fastapi.status.HTTP_201_CREATED)


async def delete_chat_user(
    selected_chat: Chat,
    chat_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    membership: ChatMembership = await validators.validate_delete_user(selected_chat, selected_user, chat_user, db)

    await db.delete(membership)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def leave_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    membership: ChatMembership = await validators.validate_leave_chat(selected_chat, selected_user, db)

    background_tasks = fastapi.background.BackgroundTasks()

    if selected_chat.chat_kind == ChatKind.PRIVATE:
        attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_chat_attachments_to_delete(selected_chat, db)
        background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

        await db.delete(selected_chat)
    else:
        await db.delete(membership)

    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def delete_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_delete_chat(selected_chat, selected_user, db)

    attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_chat_attachments_to_delete(selected_chat, db)
    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    await db.delete(selected_chat)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def create_channel(
    data: ChatNameRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    async with db.begin():
        new_chat: Chat = Chat(
        chat_kind = ChatKind.CHANNEL,
        owner_user_id = selected_user.id,
        name = data.name,
        date_and_time_created = datetime.datetime.now(datetime.timezone.utc))

        db.add(new_chat)
        await db.flush()
        await db.refresh(new_chat)

        membership: ChatMembership = ChatMembership(
        chat_id = new_chat.id,
        chat_user_id = selected_user.id,
        chat_role = ChatRole.OWNER,
        date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

        db.add(membership)

    return fastapi.responses.JSONResponse(IDModel(id = new_chat.id), status_code = fastapi.status.HTTP_201_CREATED)


async def get_user_profile(
    profile_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    user_profile_raw: Chat
    chat_name: str

    user_profile_raw, chat_name = ((await db.execute(
    sqlalchemy.select(Chat, sqlalchemy.func.coalesce(Chat.name, sqlalchemy.func.concat_ws(" ", User.name, User.surname, User.second_name)))
    .select_from(Chat)
    .where(sqlalchemy.and_(Chat.chat_kind == ChatKind.PROFILE, Chat.owner_user_id == profile_user.id))
    .join(User, User.id == Chat.owner_user_id)))
    .tuples().first())

    user_profile: ChatResponseModel = ChatResponseModel(
    id = user_profile_raw.id,
    chat_kind = user_profile_raw.chat_kind,
    name = chat_name,
    owner_user_id = user_profile_raw.owner_user_id,
    date_and_time_created = user_profile_raw.date_and_time_created)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_profile), status_code = fastapi.status.HTTP_200_OK)


async def get_chat_membership(
    selected_chat: Chat,
    selected_membership: ChatMembership,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_get_chat_membership(selected_chat, selected_membership, selected_user, db)

    chat_user: ChatMembershipResponseModel = ChatMembershipResponseModel(
    id = selected_membership.id,
    chat_id = selected_membership.chat_id,
    chat_user_id = selected_membership.chat_user_id,
    date_and_time_added = selected_membership.date_and_time_added,
    chat_role = selected_membership.chat_role)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chat_user), status_code = fastapi.status.HTTP_200_OK)