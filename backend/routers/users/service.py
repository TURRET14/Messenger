import fastapi
import fastapi.encoders
import minio.datatypes
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.asyncio
import sqlalchemy.exc
import datetime
from typing import Sequence
import urllib3

import backend.routers.dependencies
import backend.routers.security
import backend.routers.parameters as parameters
from backend.routers.errors import (ErrorRegistry)
from backend.routers.users import minio_deletion_service
from backend.storage import *
import backend.routers.chats.utils
from backend.storage.minio_handler import (MinioClient)
from backend.storage.redis_handler import (RedisClient)
import backend.routers.chats.minio_deletion_service

from request_models import (
    RegisterRequestModel,
    LoginRequestModel,
    SessionRequestModel,
    UserUpdateRequestModel,
    UserUpdateLoginRequestModel,
    UserUpdatePasswordRequestModel)

from response_models import (
    FriendRequestResponseModel,
    UserResponseModel,
    UserInListResponseModel,
    LoginResponseModel,
    SessionResponseModel)

from backend.routers.common_models import (IDModel)

import utils
import validation.validators as validators
import validation.checks as checks
import backend.routers.common_validators.validators as common_validators
import backend.routers.common_validators.checks as common_checks

async def create_user(
    data: RegisterRequestModel,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_register(data.username, data.email_address, data.login, db)

    async with db.begin():
        new_user: User = User(
        username = data.username,
        name = data.name,
        email_address = data.email_address,
        login = data.login,
        password = await backend.routers.security.hash_password(data.password),
        surname = data.surname,
        second_name = data.second_name,
        date_and_time_registered = datetime.datetime.now(datetime.timezone.utc))

        db.add(new_user)

        await db.flush()

        user_profile: Chat = Chat(owner_user_id = new_user.id, chat_kind = ChatKind.PROFILE)
        db.add(user_profile)

    await db.refresh(new_user)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = new_user.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def login(
    request: fastapi.Request,
    data: LoginRequestModel,
    db: sqlalchemy.ext.asyncio.AsyncSession,
    redis_client: RedisClient) -> fastapi.responses.Response:

    user_agent: str = await checks.check_user_agent(request.headers.get("user-agent"))

    selected_user: User = await validators.validate_login(data.login, data.password, db)

    session_id: str = await redis_client.create_user_session(selected_user.id, user_agent)

    response: fastapi.responses.Response = fastapi.responses.Response()
    response.set_cookie("session_id", value = session_id, max_age = parameters.redis_session_expiration_time_seconds, httponly = True, secure = True, samesite ="strict")
    response.status_code = fastapi.status.HTTP_204_NO_CONTENT

    return response


async def get_all_sessions(
    selected_user: User,
    redis_client: RedisClient) -> fastapi.responses.JSONResponse:

    user_session_ids: set[str] = await redis_client.get_all_user_session_ids(selected_user.id)

    user_sessions_data: list[SessionResponseModel] = []

    for session_id in user_session_ids:
        session_data: SessionModel = await validators.validate_session(session_id, selected_user, redis_client)

        user_sessions_data.append(SessionResponseModel(
        session_id = session_data.session_id,
        user_id = session_data.user_id,
        user_agent = session_data.user_agent,
        creation_datetime = session_data.creation_datetime,
        expiration_datetime = session_data.expiration_datetime))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_sessions_data), status_code = fastapi.status.HTTP_200_OK)


async def delete_session(
    data: SessionRequestModel,
    selected_user: User,
    redis_client: RedisClient) -> fastapi.responses.Response:

    session_data: SessionModel = await validators.validate_session(data.session_id, selected_user, redis_client)

    await redis_client.delete_user_session(session_data.session_id)

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def delete_all_sessions(
    selected_user: User,
    redis_client: RedisClient) -> fastapi.responses.Response:

    await redis_client.delete_all_user_sessions(selected_user.id)

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def get_user(
    selected_user: User) -> fastapi.responses.JSONResponse:

    selected_user: UserResponseModel = UserResponseModel(
        id =  selected_user.id,
        username = selected_user.username,
        name = selected_user.name,
        surname = selected_user.surname,
        second_name = selected_user.second_name,
        date_of_birth = selected_user.date_of_birth,
        gender = selected_user.gender,
        email_address = selected_user.email_address,
        phone_number = selected_user.phone_number,
        about = selected_user.about,
        date_and_time_registered = selected_user.date_and_time_registered)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(selected_user), status_code = fastapi.status.HTTP_200_OK)


async def get_user_login(
    selected_user: User) -> fastapi.responses.JSONResponse:

    user_login: LoginResponseModel = LoginResponseModel(login = selected_user.login)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_login), status_code = fastapi.status.HTTP_200_OK)


async def update_user(
    user_data: UserUpdateRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_user(selected_user, user_data.username, user_data.email_address, user_data.phone_number, db)

    selected_user.username = user_data.username
    selected_user.name = user_data.name
    selected_user.surname = user_data.surname
    selected_user.second_name = user_data.second_name
    selected_user.date_of_birth = user_data.date_of_birth
    selected_user.gender = user_data.gender
    selected_user.email_address = user_data.email_address
    selected_user.phone_number = user_data.phone_number
    selected_user.about = user_data.about

    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_user_login(
    user_login_data: UserUpdateLoginRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_user_login(selected_user, user_login_data.login, db)

    selected_user.login = user_login_data.login

    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def update_user_password(
    user_password_data: UserUpdatePasswordRequestModel,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_update_user_password(selected_user.password, user_password_data.old_password)

    selected_user.password = await backend.routers.security.hash_password(user_password_data.new_password)

    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def get_user_avatar(
    selected_user: User,
    minio_client: MinioClient) -> fastapi.responses.StreamingResponse:

    avatar_photo_path: str = await validators.validate_user_avatar(selected_user.avatar_photo_path)

    file: urllib3.BaseHTTPResponse = await minio_client.get_file(MinioBucket.users_avatars, avatar_photo_path)
    file_stat: minio.datatypes.Object = await minio_client.get_file_stat(MinioBucket.users_avatars, avatar_photo_path)

    background_tasks = fastapi.BackgroundTasks()
    background_tasks.add_task(minio_client.close_file_stream, file)

    return fastapi.responses.StreamingResponse(file.stream(), media_type = file_stat.content_type, headers = {"Content-Disposition": "inline"}, status_code = fastapi.status.HTTP_200_OK, background = background_tasks)


async def update_user_avatar(
    selected_user: User,
    file: fastapi.UploadFile,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    old_avatar_photo_path: str | None = selected_user.avatar_photo_path

    new_avatar_path: str = await minio_client.put_file(MinioBucket.users_avatars, file)
    selected_user.avatar_photo_path = new_avatar_path

    await db.commit()

    if old_avatar_photo_path:
        await minio_client.delete_file(MinioBucket.users_avatars, old_avatar_photo_path)

    return fastapi.responses.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


async def delete_user(
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_user_attachments_to_delete(selected_user, db)

    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    async with db.begin():
        await db.execute(
        sqlalchemy.delete(Chat)
        .where(Chat.id.in_(
        sqlalchemy.select(Chat.id)
        .select_from(ChatMembership)
        .where(ChatMembership.chat_user_id == selected_user.id)
        .join(Chat, Chat.id == ChatMembership.chat_id)
        .where(Chat.chat_kind == ChatKind.PRIVATE))))

        await db.delete(selected_user)

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def get_users(
    offset_multiplier: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    users_list_raw: Sequence[User] = ((await db.execute(
    sqlalchemy.select(User)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    users_list: list[UserInListResponseModel] = list()

    for user in users_list_raw:
        users_list.append(UserInListResponseModel(
        id = user.id,
        username = user.username,
        name = user.name,
        surname = user.surname,
        second_name = user.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)


async def search_users_by_username(
    offset_multiplier: int,
    search_username: str,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    users_list_raw: Sequence[User] = ((await db.execute(
    sqlalchemy.select(User)
    .where(User.username.like(f"{search_username.upper()}%"))
    .order_by(User.id).offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    users_list: list[UserInListResponseModel] = list()

    for user in users_list_raw:
        users_list.append(UserInListResponseModel(
        id = user.id,
        username = user.username,
        name = user.name,
        surname = user.surname,
        second_name = user.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def search_users_by_names(
    offset_multiplier: int,
    search_name: str | None,
    search_surname: str | None,
    search_second_name: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_user_search_parameters(search_name, search_surname, search_second_name)

    select_request = sqlalchemy.select(User)

    if search_name:
        select_request = select_request.where(User.name.like(f"{search_name.upper()}%"))
    if search_surname:
        select_request = select_request.where(User.surname.like(f"{search_surname.upper()}%"))
    if search_second_name:
        select_request = select_request.where(User.second_name.like(f"{search_second_name.upper()}%"))

    users_list_raw: Sequence[User] = ((await db.execute(
    select_request.order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    users_list: list[UserInListResponseModel] = list()

    for user in users_list_raw:
        users_list.append(UserInListResponseModel(
        id = user.id,
        username = user.username,
        name = user.name,
        surname = user.surname,
        second_name = user.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(users_list), status_code = fastapi.status.HTTP_200_OK)

async def get_friends(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friends_list_raw: Sequence[User] = ((await db.execute(
    sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.user_id == selected_user.id)
    .join(User, User.id == Friendship.friend_user_id)
    .union(
    sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.friend_user_id == selected_user.id)
    .join(User, User.id == Friendship.user_id))
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    friends_list: list[UserInListResponseModel] = list()

    for friend in friends_list_raw:
        friends_list.append(UserInListResponseModel(
        id = friend.id,
        username = friend.username,
        name = friend.name,
        surname = friend.surname,
        second_name = friend.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_username(
    offset_multiplier: int,
    username: str,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friends_list_raw: Sequence[User] = ((await db.execute(
    sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.user_id == selected_user.id)
    .join(User, User.id == Friendship.friend_user_id)
    .where(User.username.like(f"%{username}"))
    .union(
    sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.friend_user_id == selected_user.id)
    .join(User, User.id == Friendship.user_id)
    .where(User.username.like(f"{username.upper()}%")))
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    friends_list: list[UserInListResponseModel] = list()

    for friend in friends_list_raw:
        friends_list.append(UserInListResponseModel(
        id = friend.id,
        username = friend.username,
        name = friend.name,
        surname = friend.surname,
        second_name = friend.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_names(
    offset_multiplier: int,
    search_name: str | None,
    search_surname: str | None,
    search_second_name: str | None,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_user_search_parameters(search_name, search_surname, search_second_name)

    first_select_request = (sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.user_id == selected_user.id)
    .join(User, User.id == Friendship.friend_user_id))

    second_select_request = (sqlalchemy.select(User)
    .select_from(Friendship)
    .where(Friendship.friend_user_id == selected_user.id)
    .join(User, User.id == Friendship.user_id))

    if search_name:
        first_select_request = first_select_request.where(User.name.like(f"{search_name.upper()}%"))
        second_select_request = second_select_request.where(User.name.like(f"{search_name.upper()}%"))
    if search_surname:
        first_select_request = first_select_request.where(User.surname.like(f"{search_surname.upper()}%"))
        second_select_request = second_select_request.where(User.surname.like(f"{search_surname.upper()}%"))
    if search_second_name:
        first_select_request = first_select_request.where(User.second_name.like(f"{search_second_name.upper()}%"))
        second_select_request = second_select_request.where(User.second_name.like(f"{search_second_name.upper()}%"))



    friends_list_raw: Sequence[User] = ((await db.execute(
    first_select_request.union(second_select_request)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    friends_list: list[UserInListResponseModel] = list()

    for friend in friends_list_raw:
        friends_list.append(UserInListResponseModel(
        id = friend.id,
        username = friend.username,
        name = friend.name,
        surname = friend.surname,
        second_name = friend.second_name))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_sent_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friend_requests_list_raw: Sequence[FriendRequest] = ((await db.execute(
    sqlalchemy.select(FriendRequest)
    .where(FriendRequest.sender_user_id == selected_user.id)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    friend_requests_list: list[FriendRequestResponseModel] = list()

    for friend_request in friend_requests_list_raw:
        friend_requests_list.append(FriendRequestResponseModel(
        id = friend_request.id,
        date_and_time_sent = friend_request.date_and_time_sent))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_received_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friend_requests_list_raw: Sequence[FriendRequest] = ((await db.execute(
    sqlalchemy.select(FriendRequest)
    .select_from(FriendRequest)
    .where(FriendRequest.receiver_user_id == selected_user.id)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.number_of_table_entries_in_selection)
    .limit(parameters.number_of_table_entries_in_selection)))
    .scalars().all())

    friend_requests_list: list[FriendRequestResponseModel] = list()

    for friend_request in friend_requests_list_raw:
        friend_requests_list.append(FriendRequestResponseModel(
        id = friend_request.id,
        date_and_time_sent = friend_request.date_and_time_sent))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friend_requests_list), status_code = fastapi.status.HTTP_200_OK)


async def send_friend_request(
    receiver_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_send_friend_request(selected_user, receiver_user, db)

    friend_request = FriendRequest(
    sender_user_id = selected_user.id,
    receiver_user_id = receiver_user.id,
    date_and_time_sent = datetime.datetime.now(datetime.timezone.utc))

    db.add(friend_request)
    await db.commit()
    await db.refresh(friend_request)

    return fastapi.responses.JSONResponse({"id": friend_request.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def accept_friend_request(
    friend_request: FriendRequest,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_accept_friend_request(friend_request, selected_user, db)

    friendship: Friendship = Friendship(
    user_id = min(friend_request.sender_user_id, friend_request.receiver_user_id),
    friend_user_id = max(friend_request.sender_user_id, friend_request.receiver_user_id),
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    async with db.begin():
        await db.delete(friend_request)
        db.add(friendship)

    await db.refresh(friendship)

    return fastapi.responses.JSONResponse({"id": friendship.id}, status_code = fastapi.status.HTTP_201_CREATED)


async def decline_received_friend_request(
    friend_request: FriendRequest,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_decline_friend_request(friend_request, selected_user)

    await db.delete(friend_request)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def delete_sent_friend_request(
    friend_request: FriendRequest,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_delete_sent_friend_request(friend_request, selected_user)

    await db.delete(friend_request)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def delete_friend(
    friend: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    friendship: Friendship = await validators.validate_friendship(selected_user, friend, db)

    await db.delete(friendship)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def block_user(
    user_to_block: User,
    selected_user: User,
    minio_client: MinioClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_is_user_not_blocked(selected_user, user_to_block, db)

    background_tasks = fastapi.background.BackgroundTasks()

    async with db.begin():
        new_block: UserBlock = UserBlock(user_id = selected_user.id, blocked_user_id = user_to_block.id, date_and_time_blocked = datetime.datetime.now(datetime.timezone.utc))

        friendship: Friendship | None = await utils.get_friendship(selected_user, user_to_block, db)

        if friendship:
            await db.delete(friendship)

        users_chat: Chat | None = await backend.routers.chats.utils.get_users_private_chat(selected_user, user_to_block, db)
        if users_chat:
            attachments_to_delete: list[BucketWithFiles] = await backend.routers.chats.minio_deletion_service.get_all_chat_attachments_to_delete(users_chat, db)
            background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

            await db.delete(users_chat)

        friend_request_to_blocked: FriendRequest | None = await utils.get_friend_request(selected_user, user_to_block, db)
        if friend_request_to_blocked:
            await db.delete(friend_request_to_blocked)

        friend_request_from_blocked: FriendRequest | None = await utils.get_friend_request(user_to_block, selected_user, db)
        if friend_request_from_blocked:
            await db.delete(friend_request_from_blocked)

        db.add(new_block)

    await db.refresh(new_block)

    return fastapi.responses.JSONResponse({"id": new_block.id}, status_code = fastapi.status.HTTP_201_CREATED, background = background_tasks)


async def unblock_user(
    blocked_user: User,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    user_block: UserBlock = await validators.validate_is_user_blocked(selected_user, blocked_user, db)

    await db.delete(user_block)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)