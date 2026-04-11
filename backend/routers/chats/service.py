import fastapi
import fastapi.encoders
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
from typing import Sequence
import datetime

from backend.routers.chats import minio_deletion_service
from backend.routers.chats.websockets.models import ChatPubsubModel, ChatMembershipPubsubModel
from backend.routers.common_models import IDModel
from backend.storage import *
from backend.routers.chats.request_models import (ChatNameRequestModel)
from backend.routers.chats.response_models import (
    ChatResponseModel,
    ChatMembershipResponseModel,
    ChatLastMessagePreviewModel,
)
import backend.routers.errors
import backend.routers.dependencies
import backend.routers.parameters
import backend.routers.chats.utils
import backend.routers.users.utils
import backend.routers.messages.utils
from backend.routers.chats.validation import validators
import backend.routers.common_validators.validators as common_validators
import backend.routers.users.service


async def _last_root_message_preview(
    chat_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession,
) -> ChatLastMessagePreviewModel | None:

    row = (await db.execute(
        sqlalchemy.select(
            Message.message_text,
            Message.sender_user_id,
            Message.date_and_time_sent,
        )
        .where(sqlalchemy.and_(Message.chat_id == chat_id, Message.parent_message_id.is_(None)))
        .order_by(Message.date_and_time_sent.desc())
        .limit(1)
    )).first()
    if not row:
        return None
    return ChatLastMessagePreviewModel(
        message_text = row[0],
        sender_user_id = row[1],
        date_and_time_sent = row[2],
    )


async def get_private_chat_with_user(
    other_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    chat: Chat | None = await backend.routers.chats.utils.get_users_private_chat(selected_user, other_user, db)
    if not chat:
        raise fastapi.exceptions.HTTPException(status_code = backend.routers.errors.ErrorRegistry.chat_not_found_error.error_status_code, detail = backend.routers.errors.ErrorRegistry.chat_not_found_error)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = chat.id)), status_code = fastapi.status.HTTP_200_OK)


async def get_all_chats(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    subquery_chat_last_message_datetime: sqlalchemy.Subquery = (sqlalchemy.select(Message.chat_id.label("chat_id"),
    sqlalchemy.func.max(Message.date_and_time_sent).label("date_and_time_sent"))
    .select_from(Message)
    .group_by(Message.chat_id)
    .subquery())

    last_root_row = sqlalchemy.func.row_number().over(
        partition_by=Message.chat_id,
        order_by=Message.date_and_time_sent.desc(),
    ).label("last_root_rn")

    last_root_partitioned = (
        sqlalchemy.select(
            Message.chat_id,
            Message.message_text,
            Message.sender_user_id,
            Message.date_and_time_sent,
            last_root_row,
        )
        .where(Message.parent_message_id.is_(None))
        .subquery()
    )

    last_root_messages = (
        sqlalchemy.select(
            last_root_partitioned.c.chat_id,
            last_root_partitioned.c.message_text,
            last_root_partitioned.c.sender_user_id,
            last_root_partitioned.c.date_and_time_sent,
        )
        .where(last_root_partitioned.c.last_root_rn == 1)
        .subquery()
    )

    chats_list_raw: Sequence[tuple] = ((await db.execute(
    sqlalchemy.select(
    Chat,
    sqlalchemy.func.coalesce(Chat.name, sqlalchemy.select(sqlalchemy.func.concat_ws(" ", User.surname, User.name, User.second_name)).select_from(ChatMembership).where(sqlalchemy.and_(ChatMembership.chat_id == Chat.id, ChatMembership.chat_user_id != selected_user.id)).join(User, User.id == ChatMembership.chat_user_id).limit(1).scalar_subquery()).label("chat_name"),
    last_root_messages.c.message_text,
    last_root_messages.c.sender_user_id,
    last_root_messages.c.date_and_time_sent)
    .select_from(ChatMembership)
    .where(sqlalchemy.and_(ChatMembership.chat_user_id == selected_user.id))
    .join(Chat, Chat.id == ChatMembership.chat_id)
    .outerjoin(subquery_chat_last_message_datetime, subquery_chat_last_message_datetime.c.chat_id == Chat.id)
    .outerjoin(last_root_messages, last_root_messages.c.chat_id == Chat.id)
    .order_by(subquery_chat_last_message_datetime.c.date_and_time_sent.desc().nullslast(), Chat.id.desc())
    .offset(offset_multiplier * backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(backend.routers.parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .tuples().all())

    chats_list: list[ChatResponseModel] = list()

    for row in chats_list_raw:
        chat: Chat = row[0]
        chat_name: str = row[1]
        last_text: str | None = row[2]
        last_sender: int | None = row[3]
        last_sent: datetime.datetime | None = row[4]
        last_preview: ChatLastMessagePreviewModel | None = None
        if last_sent is not None or last_text is not None or last_sender is not None:
            last_preview = ChatLastMessagePreviewModel(
                message_text = last_text,
                sender_user_id = last_sender,
                date_and_time_sent = last_sent,
            )
        chats_list.append(ChatResponseModel(
        id = chat.id,
        chat_kind = chat.chat_kind,
        name = chat_name,
        owner_user_id = chat.owner_user_id,
        date_and_time_created = chat.date_and_time_created,
        has_avatar = chat.avatar_photo_path is not None,
        last_message = last_preview))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chats_list), status_code = fastapi.status.HTTP_200_OK)


async def get_chat(
    selected_chat: Chat,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    chat_name: str = await validators.validate_get_chat(selected_chat, selected_user, db)

    last_preview: ChatLastMessagePreviewModel | None = await _last_root_message_preview(selected_chat.id, db)

    chat_response = ChatResponseModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = chat_name,
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        has_avatar = selected_chat.avatar_photo_path is not None,
        last_message = last_preview)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(chat_response), status_code = fastapi.status.HTTP_200_OK)



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
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_create_private_chat(selected_user, other_user, db)

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
    await db.commit()


    await redis_client.pubsub_publish_post_chat(ChatPubsubModel(
    id = new_chat.id,
    chat_kind = new_chat.chat_kind,
    name = await backend.routers.chats.utils.get_chat_name(new_chat, selected_user, db),
    owner_user_id = new_chat.owner_user_id,
    date_and_time_created = new_chat.date_and_time_created,
    is_avatar_changed = False,
    receivers = [first_chat_user.chat_user_id, second_chat_user.chat_user_id]))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = new_chat.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def create_group_chat(
    data: ChatNameRequestModel,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

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
    await db.commit()

    await redis_client.pubsub_publish_post_chat(ChatPubsubModel(
        id = new_chat.id,
        chat_kind = new_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(new_chat, selected_user, db),
        owner_user_id = new_chat.owner_user_id,
        date_and_time_created = new_chat.date_and_time_created,
        is_avatar_changed = False,
        receivers = [membership.chat_user_id]))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = new_chat.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def update_chat_avatar(
    selected_chat: Chat,
    file: fastapi.UploadFile,
    selected_user: User,
    minio_client: MinioClient,
    redis_client: RedisClient,
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

    await redis_client.pubsub_publish_put_chat(ChatPubsubModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db),
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_avatar_changed = True,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_chat_name(
    selected_chat: Chat,
    data: ChatNameRequestModel,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_avatar_or_name(selected_chat, selected_user, db)

    selected_chat.name = data.name
    await db.commit()

    await redis_client.pubsub_publish_put_chat(ChatPubsubModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db),
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_avatar_changed = False,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_chat_owner(
    selected_chat: Chat,
    new_owner_user: User,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    old_owner_membership: ChatMembership = await common_validators.validate_chat_user_membership(selected_chat, selected_user, db)
    
    new_owner_membership: ChatMembership = await validators.validate_update_chat_owner_and_add_admin(selected_chat, selected_user, new_owner_user, db)

    selected_chat.owner_user_id = new_owner_user.id
    old_owner_membership.chat_role = ChatRole.USER
    new_owner_membership.chat_role = ChatRole.OWNER
    await db.commit()

    await redis_client.pubsub_publish_put_chat(ChatPubsubModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db),
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_avatar_changed = False,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def add_chat_admin(
    selected_chat: Chat,
    new_admin_user: User,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    new_admin_membership: ChatMembership = await validators.validate_update_chat_owner_and_add_admin(selected_chat, selected_user, new_admin_user, db)

    new_admin_membership.chat_role = ChatRole.ADMIN
    await db.commit()

    await redis_client.pubsub_publish_put_chat_membership(ChatMembershipPubsubModel(
        id = new_admin_membership.id,
        chat_user_id = new_admin_membership.chat_user_id,
        chat_id = new_admin_membership.chat_id,
        date_and_time_added = new_admin_membership.date_and_time_added,
        chat_role = new_admin_membership.chat_role,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)

async def delete_chat_admin(
    selected_chat: Chat,
    admin_user: User,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    admin_membership: ChatMembership = await validators.validate_delete_chat_admin(selected_chat, selected_user, admin_user, db)

    admin_membership.chat_role = ChatRole.USER
    await db.commit()

    await redis_client.pubsub_publish_put_chat_membership(ChatMembershipPubsubModel(
        id = admin_membership.id,
        chat_user_id = admin_membership.chat_user_id,
        chat_id = admin_membership.chat_id,
        date_and_time_added = admin_membership.date_and_time_added,
        chat_role = admin_membership.chat_role,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def add_chat_user(
    selected_chat: Chat,
    new_user: User,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_add_user(selected_chat, selected_user, new_user, db)

    membership: ChatMembership = ChatMembership(
    chat_id = selected_chat.id,
    chat_user_id = new_user.id,
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc),
    chat_role = ChatRole.USER)

    db.add(membership)
    await db.commit()

    await redis_client.pubsub_publish_post_chat_membership(ChatMembershipPubsubModel(
        id = membership.id,
        chat_user_id = membership.chat_user_id,
        chat_id = membership.chat_id,
        date_and_time_added = membership.date_and_time_added,
        chat_role = membership.chat_role,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db, membership.chat_user_id)))

    await redis_client.pubsub_publish_post_chat(ChatPubsubModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db),
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_avatar_changed = True,
        receivers = [membership.chat_user_id]))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = membership.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def delete_chat_user(
    selected_chat: Chat,
    chat_user: User,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    membership: ChatMembership = await validators.validate_delete_user(selected_chat, selected_user, chat_user, db)

    await db.delete(membership)
    await db.commit()

    await redis_client.pubsub_publish_delete_chat_membership(ChatMembershipPubsubModel(
        id = membership.id,
        chat_user_id = membership.chat_user_id,
        chat_id = membership.chat_id,
        date_and_time_added = membership.date_and_time_added,
        chat_role = membership.chat_role,
        receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db, membership.chat_user_id)))

    await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
        id = selected_chat.id,
        chat_kind = selected_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db),
        owner_user_id = selected_chat.owner_user_id,
        date_and_time_created = selected_chat.date_and_time_created,
        is_avatar_changed = True,
        receivers = [membership.chat_user_id]))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def leave_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: MinioClient,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    membership: ChatMembership = await validators.validate_leave_chat(selected_chat, selected_user, db)

    background_tasks = fastapi.background.BackgroundTasks()

    chat_member_ids: list[int] = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)
    chat_name: str = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db)

    if selected_chat.chat_kind == ChatKind.PRIVATE:
        attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_chat_attachments_to_delete(selected_chat, db)
        background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

        await db.delete(selected_chat)
    else:
        await db.delete(membership)

    await db.commit()

    if selected_chat.chat_kind == ChatKind.PRIVATE:
        await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
            id = selected_chat.id,
            chat_kind = selected_chat.chat_kind,
            name = chat_name,
            owner_user_id = selected_chat.owner_user_id,
            date_and_time_created = selected_chat.date_and_time_created,
            is_avatar_changed = False,
            receivers = chat_member_ids))
    else:
        await redis_client.pubsub_publish_delete_chat_membership(ChatMembershipPubsubModel(
            id = membership.id,
            chat_user_id = membership.chat_user_id,
            chat_id = membership.chat_id,
            date_and_time_added = membership.date_and_time_added,
            chat_role = membership.chat_role,
            receivers = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db, membership.chat_user_id)))

        await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
            id = selected_chat.id,
            chat_kind = selected_chat.chat_kind,
            name = chat_name,
            owner_user_id = selected_chat.owner_user_id,
            date_and_time_created = selected_chat.date_and_time_created,
            is_avatar_changed = False,
            receivers = [membership.chat_user_id]))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def delete_chat(
    selected_chat: Chat,
    selected_user: User,
    minio_client: MinioClient,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_delete_chat(selected_chat, selected_user, db)

    chat_member_ids: list[int] = await backend.routers.chats.utils.get_chat_member_ids(selected_chat, db)
    chat_name: str = await backend.routers.chats.utils.get_chat_name(selected_chat, selected_user, db)

    attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_chat_attachments_to_delete(selected_chat, db)
    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    await db.delete(selected_chat)
    await db.commit()

    await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
            id = selected_chat.id,
            chat_kind = selected_chat.chat_kind,
            name = chat_name,
            owner_user_id = selected_chat.owner_user_id,
            date_and_time_created = selected_chat.date_and_time_created,
            is_avatar_changed = False,
            receivers = chat_member_ids))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def create_channel(
    data: ChatNameRequestModel,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

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
    await db.commit()

    await redis_client.pubsub_publish_post_chat(ChatPubsubModel(
        id = new_chat.id,
        chat_kind = new_chat.chat_kind,
        name = await backend.routers.chats.utils.get_chat_name(new_chat, selected_user, db),
        owner_user_id = new_chat.owner_user_id,
        date_and_time_created = new_chat.date_and_time_created,
        is_avatar_changed = False,
        receivers = [membership.chat_user_id]))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = new_chat.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def get_user_profile(
    profile_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    user_profile_raw: Chat
    chat_name: str

    row = ((await db.execute(
    sqlalchemy.select(Chat, sqlalchemy.func.coalesce(Chat.name, sqlalchemy.func.concat_ws(" ", User.surname, User.name, User.second_name)))
    .select_from(Chat)
    .where(sqlalchemy.and_(Chat.chat_kind == ChatKind.PROFILE, Chat.owner_user_id == profile_user.id))
    .join(User, User.id == Chat.owner_user_id)))
    .tuples().first())

    if not row:
        raise fastapi.exceptions.HTTPException(status_code = backend.routers.errors.ErrorRegistry.chat_not_found_error.error_status_code, detail = backend.routers.errors.ErrorRegistry.chat_not_found_error)

    user_profile_raw: Chat
    chat_name: str
    user_profile_raw, chat_name = row

    last_preview: ChatLastMessagePreviewModel | None = await _last_root_message_preview(user_profile_raw.id, db)

    user_profile: ChatResponseModel = ChatResponseModel(
    id = user_profile_raw.id,
    chat_kind = user_profile_raw.chat_kind,
    name = chat_name,
    owner_user_id = user_profile_raw.owner_user_id,
    date_and_time_created = user_profile_raw.date_and_time_created,
    has_avatar = user_profile_raw.avatar_photo_path is not None,
    last_message = last_preview)

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
