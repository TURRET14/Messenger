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
from starlette.status import HTTP_204_NO_CONTENT

import backend.environment as environment
import backend.routers.dependencies
import backend.routers.security
import backend.routers.parameters as parameters
from backend.routers.chats.websockets.models import ChatPubsubModel
from backend.routers.errors import ErrorRegistry
from backend.routers.users import minio_deletion_service
from backend.storage import *
import backend.routers.chats.utils
from backend.storage.minio_handler import (MinioClient)
from backend.storage.redis_handler import (RedisClient)
import backend.routers.chats.minio_deletion_service
from backend.routers.users import utils
from backend.routers.users.validation import validators
from backend.routers.users.validation import checks
from backend.routers.users.request_models import (
    RegisterRequestModel,
    LoginRequestModel,
    SessionRequestModel,
    UserUpdateRequestModel,
    UserUpdateLoginRequestModel,
    UserUpdatePasswordRequestModel,
    CodeModel,
    EmailRequestModel,
    PasswordResetConfirmRequestModel)

from backend.routers.users.response_models import (
    FriendRequestResponseModel,
    UserResponseModel,
    UserInListResponseModel,
    LoginResponseModel,
    SessionResponseModel,
    CurrentUserResponseModel,
    FriendUserInListResponseModel, UserBlockResponseModel)

from backend.routers.common_models import (IDModel)
from backend.email_service import EmailService


async def register(
    data: RegisterRequestModel,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_register(data.username, data.email_address, data.login, db)

    register_session_code: str = await redis_client.create_register_session(data)

    await EmailService.send_registration_confirmation(data.email_address, register_session_code)

    return fastapi.responses.Response(status_code = HTTP_204_NO_CONTENT)


async def create_user(
    register_session: CodeModel,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    register_data: RegisterRequestModel | None = await redis_client.get_register_session(register_session.code)

    if not register_data:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_email_code_error.error_status_code, detail = ErrorRegistry.invalid_email_code_error)

    await validators.validate_register(register_data.username, register_data.email_address, register_data.login, db)

    new_user: User = User(
        username = register_data.username,
        name = register_data.name,
        email_address = register_data.email_address,
        login = register_data.login,
        password = await backend.routers.security.hash_password(register_data.password),
        surname = register_data.surname,
        second_name = register_data.second_name,
        date_and_time_registered = datetime.datetime.now(datetime.timezone.utc))

    db.add(new_user)

    await db.flush()
    await db.refresh(new_user)

    user_profile: Chat = Chat(
        owner_user_id = new_user.id,
        chat_kind = ChatKind.PROFILE,
        date_and_time_created = datetime.datetime.now(datetime.timezone.utc))
    db.add(user_profile)
    await db.commit()

    await redis_client.delete_register_session(register_session.code)

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
    response.set_cookie(
        "session_id",
        value = session_id,
        max_age = parameters.REDIS_USER_SESSION_EXPIRATION_TIME_SECONDS,
        httponly = True,
        secure = environment.FRONTEND_URL.startswith("https://"),
        samesite = "strict")
    response.status_code = fastapi.status.HTTP_200_OK

    return response


async def request_password_reset(
    email_data: EmailRequestModel,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    selected_user: User | None = ((await db.execute(
    sqlalchemy.select(User)
    .where(User.email_address == email_data.email_address)))
    .scalars().first())

    if not selected_user:
        return fastapi.responses.Response(status_code = HTTP_204_NO_CONTENT)

    request_code: str = await redis_client.create_password_reset_request(selected_user.id)
    try:
        await EmailService.send_password_reset_code(email_data.email_address, request_code)
    except fastapi.exceptions.HTTPException:
        await redis_client.delete_password_reset_request(request_code)
        raise

    return fastapi.responses.Response(status_code = HTTP_204_NO_CONTENT)


async def confirm_password_reset(
    password_reset_data: PasswordResetConfirmRequestModel,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    password_reset_request = await redis_client.get_password_reset_request(password_reset_data.code)

    if not password_reset_request:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_email_code_error.error_status_code, detail = ErrorRegistry.invalid_email_code_error)

    selected_user: User | None = ((await db.execute(
    sqlalchemy.select(User)
    .where(User.id == password_reset_request.user_id)))
    .scalars().first())

    if not selected_user:
        await redis_client.delete_password_reset_request(password_reset_data.code)
        return fastapi.responses.Response(status_code = HTTP_204_NO_CONTENT)

    selected_user.password = await backend.routers.security.hash_password(password_reset_data.new_password)
    await db.commit()

    await redis_client.delete_password_reset_request(password_reset_data.code)
    await redis_client.delete_all_user_sessions(selected_user.id)

    return fastapi.responses.Response(status_code = HTTP_204_NO_CONTENT)


async def get_all_sessions(
    selected_user: User,
    redis_client: RedisClient) -> fastapi.responses.JSONResponse:

    user_sessions_data_list_raw: list[SessionModel] = await redis_client.get_all_user_sessions_data(selected_user.id)

    user_sessions_data_list: list[SessionResponseModel] = []

    for session_data in user_sessions_data_list_raw:
        user_sessions_data_list.append(SessionResponseModel(
        session_id = session_data.session_id,
        user_id = session_data.user_id,
        user_agent = session_data.user_agent,
        creation_datetime = session_data.creation_datetime,
        expiration_datetime = session_data.expiration_datetime))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_sessions_data_list), status_code = fastapi.status.HTTP_200_OK)


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
    selected_user: User,
    is_current_user: bool) -> fastapi.responses.JSONResponse:

    if is_current_user:
        user_data: CurrentUserResponseModel | UserResponseModel = CurrentUserResponseModel(
            id = selected_user.id,
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
    else:
        user_data = UserResponseModel(
            id = selected_user.id,
            username = selected_user.username,
            name = selected_user.name,
            surname = selected_user.surname,
            second_name = selected_user.second_name,
            date_of_birth = selected_user.date_of_birth,
            gender = selected_user.gender,
            phone_number = selected_user.phone_number,
            about = selected_user.about,
            date_and_time_registered = selected_user.date_and_time_registered)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(user_data), status_code = fastapi.status.HTTP_200_OK)


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


async def update_user_email(
    email_data: EmailRequestModel,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    if selected_user.email_address == email_data.email_address:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.bad_request_error.error_status_code, detail = ErrorRegistry.bad_request_error)

    await checks.check_is_email_address_not_taken(email_data.email_address, db)

    code: str = await redis_client.create_change_email_request(selected_user.id, email_data)
    try:
        await EmailService.send_email_change_confirmation(email_data.email_address, code)
    except fastapi.exceptions.HTTPException:
        await redis_client.delete_change_email_request(code)
        raise

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def confirm_update_user_email(
    confirmation_code: CodeModel,
    selected_user: User,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession):

    update_user_email_request_data: ChangeEmailRequestModel | None = await redis_client.get_change_email_request(confirmation_code.code)

    if not update_user_email_request_data:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.invalid_email_code_error.error_status_code, detail = ErrorRegistry.invalid_email_code_error)

    if update_user_email_request_data.user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.forbidden_error.error_status_code, detail = ErrorRegistry.forbidden_error)

    if selected_user.email_address == update_user_email_request_data.new_email_address:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.bad_request_error.error_status_code, detail = ErrorRegistry.bad_request_error)

    await checks.check_is_email_address_not_taken(update_user_email_request_data.new_email_address, db)

    selected_user.email_address = update_user_email_request_data.new_email_address

    await db.commit()

    await redis_client.delete_change_email_request(confirmation_code.code)

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
    new_avatar_photo_path: str = await minio_client.put_file(MinioBucket.users_avatars, file)
    try:
        selected_user.avatar_photo_path = new_avatar_photo_path
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await minio_client.delete_file(MinioBucket.users_avatars, new_avatar_photo_path)

        raise

    if old_avatar_photo_path:
        await minio_client.delete_file(MinioBucket.users_avatars, old_avatar_photo_path)

    return fastapi.responses.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


async def delete_user(
    selected_user: User,
    minio_client: MinioClient,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    attachments_to_delete: list[BucketWithFiles] = await minio_deletion_service.get_all_user_attachments_to_delete(selected_user, db)

    background_tasks = fastapi.background.BackgroundTasks()
    background_tasks.add_task(minio_client.delete_all_files, attachments_to_delete)

    chat_users_dict: dict[Chat, list[int]] = {}
    user_chats_for_deletion: Sequence[Chat] = await backend.routers.users.utils.get_all_user_dependent_chats(selected_user, db)
    for chat in user_chats_for_deletion:
        chat_users_dict[chat] = await backend.routers.chats.utils.get_chat_member_ids(chat, db)

    await db.execute(
    sqlalchemy.delete(Chat)
    .where(Chat.id.in_(
    sqlalchemy.select(Chat.id)
    .select_from(ChatMembership)
    .where(ChatMembership.chat_user_id == selected_user.id)
    .join(Chat, Chat.id == ChatMembership.chat_id)
    .where(Chat.chat_kind == ChatKind.PRIVATE))))

    await db.delete(selected_user)
    await db.commit()

    for chat, chat_members in chat_users_dict.items():
        await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
            id = chat.id,
            chat_kind = chat.chat_kind,
            name = str(chat.name or ""),
            owner_user_id = chat.owner_user_id,
            date_and_time_created = chat.date_and_time_created,
            is_avatar_changed = False,
            receivers = chat_members))

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT, background = background_tasks)


async def get_users(
    offset_multiplier: int,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    users_list_raw: Sequence[User] = ((await db.execute(
    sqlalchemy.select(User)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
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
    .where(User.username.ilike(f"{search_username}%"))
    .order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
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
        select_request = select_request.where(User.name.ilike(f"{search_name}%"))
    if search_surname:
        select_request = select_request.where(User.surname.ilike(f"{search_surname}%"))
    if search_second_name:
        select_request = select_request.where(User.second_name.ilike(f"{search_second_name}%"))

    users_list_raw: Sequence[User] = ((await db.execute(
    select_request.order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
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

    friends_side_a = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.friend_user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.user_id == selected_user.id)
    friends_side_b = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.friend_user_id == selected_user.id)
    friends_subquery = sqlalchemy.union_all(friends_side_a, friends_side_b).subquery()

    friends_list_raw: Sequence[tuple[User, int, datetime.datetime]] = ((await db.execute(
    sqlalchemy.select(User, friends_subquery.c.friendship_id, friends_subquery.c.date_and_time_added)
    .select_from(friends_subquery)
    .join(User, User.id == friends_subquery.c.friend_id)
    .order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .tuples().all())

    friends_list: list[FriendUserInListResponseModel] = list()

    for friend_user, friendship_id, date_and_time_added in friends_list_raw:
        friends_list.append(FriendUserInListResponseModel(
        id = friend_user.id,
        username = friend_user.username,
        name = friend_user.name,
        surname = friend_user.surname,
        second_name = friend_user.second_name,
        friendship_id = friendship_id,
        date_and_time_added = date_and_time_added))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_username(
    offset_multiplier: int,
    username: str,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friends_side_a = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.friend_user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.user_id == selected_user.id)
    friends_side_b = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.friend_user_id == selected_user.id)
    friends_subquery = sqlalchemy.union_all(friends_side_a, friends_side_b).subquery()

    friends_list_raw: Sequence[tuple[User, int, datetime.datetime]] = ((await db.execute(
    sqlalchemy.select(User, friends_subquery.c.friendship_id, friends_subquery.c.date_and_time_added)
    .select_from(friends_subquery)
    .join(User, User.id == friends_subquery.c.friend_id)
    .where(User.username.ilike(f"{username}%"))
    .order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .tuples().all())

    friends_list: list[FriendUserInListResponseModel] = list()

    for friend_user, friendship_id, date_and_time_added in friends_list_raw:
        friends_list.append(FriendUserInListResponseModel(
        id = friend_user.id,
        username = friend_user.username,
        name = friend_user.name,
        surname = friend_user.surname,
        second_name = friend_user.second_name,
        friendship_id = friendship_id,
        date_and_time_added = date_and_time_added))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def search_friends_by_names(
    offset_multiplier: int,
    search_name: str | None,
    search_surname: str | None,
    search_second_name: str | None,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_user_search_parameters(search_name, search_surname, search_second_name)

    friends_side_a = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.friend_user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.user_id == selected_user.id)
    friends_side_b = sqlalchemy.select(
        Friendship.id.label("friendship_id"),
        Friendship.user_id.label("friend_id"),
        Friendship.date_and_time_added.label("date_and_time_added"),
    ).where(Friendship.friend_user_id == selected_user.id)
    friends_subquery = sqlalchemy.union_all(friends_side_a, friends_side_b).subquery()

    select_request = (
    sqlalchemy.select(User, friends_subquery.c.friendship_id, friends_subquery.c.date_and_time_added)
    .select_from(friends_subquery)
    .join(User, User.id == friends_subquery.c.friend_id))

    if search_name:
        select_request = select_request.where(User.name.ilike(f"{search_name}%"))
    if search_surname:
        select_request = select_request.where(User.surname.ilike(f"{search_surname}%"))
    if search_second_name:
        select_request = select_request.where(User.second_name.ilike(f"{search_second_name}%"))

    friends_list_raw: Sequence[tuple[User, int, datetime.datetime]] = ((await db.execute(
    select_request.order_by(User.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .tuples().all())

    friends_list: list[FriendUserInListResponseModel] = list()

    for friend_user, friendship_id, date_and_time_added in friends_list_raw:
        friends_list.append(FriendUserInListResponseModel(
        id = friend_user.id,
        username = friend_user.username,
        name = friend_user.name,
        surname = friend_user.surname,
        second_name = friend_user.second_name,
        friendship_id = friendship_id,
        date_and_time_added = date_and_time_added))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(friends_list), status_code = fastapi.status.HTTP_200_OK)


async def get_user_sent_friend_requests(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    friend_requests_list_raw: Sequence[FriendRequest] = ((await db.execute(
    sqlalchemy.select(FriendRequest)
    .where(FriendRequest.sender_user_id == selected_user.id)
    .order_by(FriendRequest.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .scalars().all())

    friend_requests_list: list[FriendRequestResponseModel] = list()

    for friend_request in friend_requests_list_raw:
        friend_requests_list.append(FriendRequestResponseModel(
        id = friend_request.id,
        receiver_user_id = friend_request.receiver_user_id,
        sender_user_id = friend_request.sender_user_id,
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
    .order_by(FriendRequest.id)
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .scalars().all())

    friend_requests_list: list[FriendRequestResponseModel] = list()

    for friend_request in friend_requests_list_raw:
        friend_requests_list.append(FriendRequestResponseModel(
        id = friend_request.id,
        receiver_user_id = friend_request.receiver_user_id,
        sender_user_id = friend_request.sender_user_id,
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

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = friend_request.id)), status_code = fastapi.status.HTTP_201_CREATED)


async def accept_friend_request(
    friend_request: FriendRequest,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_accept_friend_request(friend_request, selected_user, db)

    friendship: Friendship = Friendship(
    user_id = min(friend_request.sender_user_id, friend_request.receiver_user_id),
    friend_user_id = max(friend_request.sender_user_id, friend_request.receiver_user_id),
    date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    await db.delete(friend_request)
    db.add(friendship)
    await db.commit()

    await db.refresh(friendship)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = friendship.id)), status_code = fastapi.status.HTTP_201_CREATED)


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


async def delete_friendship(
    friendship: Friendship,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_friendship(friendship, selected_user)

    await db.delete(friendship)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def block_user(
    user_to_block: User,
    selected_user: User,
    minio_client: MinioClient,
    redis_client: RedisClient,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    await validators.validate_is_user_not_blocked(selected_user, user_to_block, db)

    background_tasks = fastapi.background.BackgroundTasks()

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
    await db.commit()

    if users_chat:
        await redis_client.pubsub_publish_delete_chat(ChatPubsubModel(
            id = users_chat.id,
            chat_kind = users_chat.chat_kind,
            name = str(users_chat.name or ""),
            owner_user_id = users_chat.owner_user_id,
            date_and_time_created = users_chat.date_and_time_created,
            is_avatar_changed = False,
            receivers = [selected_user.id, user_to_block.id]))

    await db.refresh(new_block)

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(IDModel(id = new_block.id)), status_code = fastapi.status.HTTP_201_CREATED, background = background_tasks)


async def unblock_user(
    user_block: UserBlock,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.Response:

    await validators.validate_is_user_block_creator(user_block, selected_user)

    await db.delete(user_block)
    await db.commit()

    return fastapi.responses.Response(status_code = fastapi.status.HTTP_204_NO_CONTENT)


async def get_blocks(
    offset_multiplier: int,
    selected_user: User,
    db: sqlalchemy.ext.asyncio.AsyncSession) -> fastapi.responses.JSONResponse:

    blocks_list_raw: Sequence[UserBlock] = ((await db.execute(
    sqlalchemy.select(UserBlock)
    .where(UserBlock.user_id == selected_user.id)
    .order_by(UserBlock.date_and_time_blocked.desc())
    .offset(offset_multiplier * parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)
    .limit(parameters.NUMBER_OF_DATABASE_TABLE_ROWS_IN_SELECTION)))
    .scalars().all())

    blocks_list: list[UserBlockResponseModel] = list()

    for block in blocks_list_raw:
        blocks_list.append(UserBlockResponseModel(
        id = block.id,
        user_id = block.user_id,
        blocked_user_id = block.blocked_user_id,
        date_and_time_blocked = block.date_and_time_blocked))

    return fastapi.responses.JSONResponse(fastapi.encoders.jsonable_encoder(blocks_list), status_code = fastapi.status.HTTP_200_OK)
