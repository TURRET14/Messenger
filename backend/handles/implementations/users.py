import datetime
import uuid

import fastapi
import minio.datatypes
import sqlalchemy
import sqlalchemy.orm
import pathlib

import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.database
import backend.authorization.sessions
import backend.authorization.password_hashing
import backend.storage.minio
import backend.parameters


async def get_user_by_id(
    user_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    selected_user: backend.storage.database.User | None = (db.execute(sqlalchemy.select(
    backend.storage.database.User.id,
    backend.storage.database.User.username,
    backend.storage.database.User.name,
    backend.storage.database.User.surname,
    backend.storage.database.User.second_name,
    backend.storage.database.User.date_of_birth,
    backend.storage.database.User.gender,
    backend.storage.database.User.email_address,
    backend.storage.database.User.phone_number,
    backend.storage.database.User.country,
    backend.storage.database.User.city,
    backend.storage.database.User.about,
    backend.storage.database.User.date_and_time_registered,
    backend.storage.database.User.messenger_role)
    .where(backend.storage.database.User.id == user_id)).scalar())
    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    return fastapi.responses.JSONResponse(selected_user, status_code=fastapi.status.HTTP_200_OK)


async def update_user(
    data: backend.models.pydantic_request_models.UserUpdateModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(sqlalchemy.and_(backend.storage.database.User.username == data.username, backend.storage.database.User.id != selected_user.id))).scalar() is not None:
        return fastapi.responses.JSONResponse("USERNAME_ALREADY_TAKEN", status_code=fastapi.status.HTTP_409_CONFLICT)
    if db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(sqlalchemy.and_(backend.storage.database.User.email_address == data.email_address, backend.storage.database.User.id != selected_user.id))).scalar() is not None:
        return fastapi.responses.JSONResponse("EMAIL_ALREADY_TAKEN", status_code=fastapi.status.HTTP_409_CONFLICT)
    if db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(sqlalchemy.and_(backend.storage.database.User.phone_number == data.phone_number, backend.storage.database.User.id != selected_user.id))).scalar() is not None:
        return fastapi.responses.JSONResponse("PHONE_NUMBER_ALREADY_TAKEN", status_code=fastapi.status.HTTP_409_CONFLICT)

    selected_user.username = data.username
    selected_user.name = data.name
    selected_user.surname = data.surname
    selected_user.second_name = data.second_name
    selected_user.date_of_birth = data.date_of_birth
    selected_user.gender = data.gender
    selected_user.email_address = data.email_address
    selected_user.phone_number = data.phone_number
    selected_user.country = data.country
    selected_user.city = data.city
    selected_user.about = data.about
    db.commit()
    return fastapi.responses.JSONResponse("SUCCESS", status_code = fastapi.status.HTTP_200_OK)


async def update_user_login(
    data: backend.models.pydantic_request_models.UserUpdateLoginModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User)
    .where(backend.storage.database.User.login == selected_user.login)).first() is not None:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "LOGIN_ALREADY_TAKEN_ERROR")

    selected_user.login = data.login
    db.commit()
    return fastapi.responses.JSONResponse("SUCCESS", status_code = fastapi.status.HTTP_200_OK)


async def update_user_password(
    data: backend.models.pydantic_request_models.UserUpdatePasswordModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")

    backend.authorization.password_hashing.verify_password(selected_user.password, data.old_password)

    selected_user.password = backend.authorization.password_hashing.hash_password(data.password)
    db.commit()
    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)

async def get_user_avatar_by_id(
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.StreamingResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")
    if not selected_user.avatar_photo_path:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "AVATAR_NOT_FOUND_ERROR")

    file_coroutine = minio_client.get_user_avatar_object(selected_user.avatar_photo_path)
    file_stat_coroutine = minio_client.get_user_avatar_stat(selected_user.avatar_photo_path)

    file: minio.datatypes.BaseHTTPResponse = await file_coroutine
    file_stat: minio.datatypes.Object = await file_stat_coroutine

    return fastapi.responses.StreamingResponse(file.stream(32*1024), media_type=file_stat.content_type, headers={"Content-Disposition": "inline"}, status_code=fastapi.status.HTTP_200_OK)


async def update_user_avatar(
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    file: fastapi.UploadFile = fastapi.File(),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if file.content_type not in backend.parameters.allowed_image_content_types:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "IMAGE_TYPE_NOT_ALLOWED_ERROR")

    image_extension: str = pathlib.Path(file.filename).suffix.upper()

    if image_extension not in backend.parameters.allowed_image_extensions:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "IMAGE_TYPE_NOT_ALLOWED_ERROR")

    if file.size > 50 * 1024 * 1024:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="IMAGE_SIZE_TOO_LARGE_ERROR")

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")

    minio_file_name: str = f"${selected_user.id}/${uuid.uuid4().hex.upper()}${image_extension}"
    await backend.storage.minio.get_minio_client().upload_user_avatar(minio_file_name, file)

    if selected_user.avatar_photo_path is not None:
        await minio_client.delete_user_avatar(selected_user.avatar_photo_path)

    selected_user.avatar_photo_path = minio_file_name
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)


async def delete_user(
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    minio_client: backend.storage.minio.MinioClient = fastapi.Depends(backend.storage.minio.get_minio_client),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = "USER_NOT_FOUND_ERROR")

    if selected_user.avatar_photo_path:
        await minio_client.delete_user_avatar(selected_user.avatar_photo_path)

    db.delete(selected_user)
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)


def get_users_by_username(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    username: str = fastapi.Query(),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(db.execute(sqlalchemy.select(
    backend.storage.database.User.id,
    backend.storage.database.User.username,
    backend.storage.database.User.name,
    backend.storage.database.User.surname,
    backend.storage.database.User.second_name)
    .where(backend.storage.database.User.username.like(f"%${username}"))
    .order_by(backend.storage.database.User.id).offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all(), status_code=fastapi.status.HTTP_200_OK)

async def get_users_by_names(
        offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
        name: str | None = fastapi.Query(),
        surname: str | None = fastapi.Query(),
        second_name: str | None = fastapi.Query(),
        db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:
    if name is None and surname is None and second_name is None:
        raise fastapi.exceptions.HTTPException(detail = "NO_ARGUMENTS_PROVIDED", status_code = fastapi.status.HTTP_400_NOT_FOUND)

    select_request = sqlalchemy.select(
    backend.storage.database.User.id,
    backend.storage.database.User.username,
    backend.storage.database.User.name,
    backend.storage.database.User.surname,
    backend.storage.database.User.second_name)

    if name is not None:
        select_request = select_request.where(backend.storage.database.User.name.like(f"%${name}"))
    if surname is not None:
        select_request = select_request.where(backend.storage.database.User.surname.like(f"%${surname}"))
    if second_name is not None:
        select_request = select_request.where(backend.storage.database.User.second_name.like(f"%${second_name}"))

    select_request = select_request.order_by(backend.storage.database.User.id).offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection).limit(backend.parameters.number_of_table_entries_in_selection)
    return fastapi.responses.JSONResponse(db.execute(select_request).scalars().all(), status_code=fastapi.status.HTTP_200_OK)

async def get_user_friends(
        offset_multiplier: int = fastapi.Query(default=0, ge=0),
        selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
        db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(db.execute((sqlalchemy.select(
        backend.storage.database.User.id,
        backend.storage.database.User.username,
        backend.storage.database.User.name,
        backend.storage.database.User.surname,
        backend.storage.database.User.second_name)
        .select_from(backend.storage.database.UserFriend)
        .where(backend.storage.database.UserFriend.user_id == selected_user.id)
        .join(backend.storage.database.User,
        backend.storage.database.User.id == backend.storage.database.UserFriend.friend_user_id)
        .union(
        sqlalchemy.select(
        backend.storage.database.User.id,
        backend.storage.database.User.username,
        backend.storage.database.User.name,
        backend.storage.database.User.surname,
        backend.storage.database.User.second_name)
        .select_from(backend.storage.database.UserFriend)
        .where(backend.storage.database.UserFriend.friend_user_id == selected_user.id)
        .join(backend.storage.database.User, backend.storage.database.User.id == backend.storage.database.UserFriend.user_id)))
        .order_by(backend.storage.database.User.id)
        .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection).limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all(),
        status_code = fastapi.status.HTTP_200_OK)


async def get_user_sent_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(db.execute(
        sqlalchemy.select(
        backend.storage.database.User.id,
        backend.storage.database.User.username,
        backend.storage.database.User.name,
        backend.storage.database.User.surname,
        backend.storage.database.User.second_name,
        backend.storage.database.UserFriendRequest.date_and_time_sent)
        .select_from(backend.storage.database.UserFriendRequest)
        .where(backend.storage.database.UserFriendRequest.sender_user_id == selected_user.id)
        .join(backend.storage.database.User, backend.storage.database.User.id == backend.storage.database.UserFriendRequest.sender_user_id)
        .order_by(backend.storage.database.User.id)
        .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
        .limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all(),
        status_code=fastapi.status.HTTP_200_OK)


async def get_user_received_friend_requests(
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    return fastapi.responses.JSONResponse(db.execute(
        sqlalchemy.select(
        backend.storage.database.User.id,
        backend.storage.database.User.username,
        backend.storage.database.User.name,
        backend.storage.database.User.surname,
        backend.storage.database.User.second_name,
        backend.storage.database.UserFriendRequest.date_and_time_sent)
        .select_from(backend.storage.database.UserFriendRequest)
        .where(backend.storage.database.UserFriendRequest.receiver_user_id == selected_user.id)
        .join(backend.storage.database.User, backend.storage.database.User.id == backend.storage.database.UserFriendRequest.sender_user_id)
        .order_by(backend.storage.database.User.id)
        .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
        .limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all(),
        status_code=fastapi.status.HTTP_200_OK)


async def send_friend_request(
    data: backend.models.pydantic_request_models.UserIDModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    if data.id == selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "INCORRECT_FRIEND_ERROR")

    if (db.execute(sqlalchemy.select(backend.storage.database.UserFriendRequest).where(
    sqlalchemy.and_(backend.storage.database.UserFriendRequest.sender_user_id == selected_user.id,
    backend.storage.database.UserFriendRequest.receiver_user_id == data.id))).scalar()
    is not None or db.execute(sqlalchemy.select(backend.storage.database.UserFriendRequest)
    .where(sqlalchemy.and_(backend.storage.database.UserFriendRequest.sender_user_id == data.id,
                           backend.storage.database.UserFriendRequest.receiver_user_id == selected_user.id))).scalar() is not None):
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="FRIEND_REQUEST_ALREADY_EXISTS_ERROR")

    if db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.id == data.id)).scalar() is None:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND_ERROR")

    friend_request = backend.storage.database.UserFriendRequest()
    friend_request.sender_user_id = selected_user.id
    friend_request.receiver_user_id = data.id
    friend_request.date_and_time_sent = datetime.datetime.now(datetime.timezone.utc)
    db.add(friend_request)
    db.commit()
    return fastapi.responses.JSONResponse("SUCCESS", status_code = fastapi.status.HTTP_201_CREATED)


async def accept_friend_request(
    data: backend.models.pydantic_request_models.UserIDModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    friend_request = db.execute(sqlalchemy.select(backend.storage.database.UserFriendRequest)
    .where(sqlalchemy.and_(backend.storage.database.UserFriendRequest.receiver_user_id == selected_user.id,
    backend.storage.database.UserFriendRequest.sender_user_id == data.id))).scalar()
    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="FRIEND_REQUEST__NOT_FOUND_ERROR")

    user_friend: backend.storage.database.UserFriend = backend.storage.database.UserFriend(user_id = selected_user.id,
    friend_user_id = data.id, date_and_time_added = datetime.datetime.now(datetime.timezone.utc))

    db.add(user_friend)
    db.commit()

    db.delete(friend_request)

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_201_CREATED)


async def decline_received_friend_request(
    data: backend.models.pydantic_request_models.UserIDModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    friend_request: backend.storage.database.UserFriendRequest = db.execute(sqlalchemy.select(backend.storage.database.UserFriendRequest)
    .where(sqlalchemy.and_(backend.storage.database.UserFriendRequest.receiver_user_id == selected_user.id,
    backend.storage.database.UserFriendRequest.sender_user_id == data.id))).scalar()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="FRIEND_REQUEST__NOT_FOUND_ERROR")

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)


async def delete_sent_friend_request(
    data: backend.models.pydantic_request_models.UserIDModel = fastapi.Body(),
    selected_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:


    friend_request: backend.storage.database.UserFriendRequest = db.execute(sqlalchemy.select(backend.storage.database.UserFriendRequest)
    .where(sqlalchemy.and_(backend.storage.database.UserFriendRequest.receiver_user_id == data.id,
    backend.storage.database.UserFriendRequest.sender_user_id == selected_user.id))).scalar()

    if not friend_request:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="FRIEND_REQUEST__NOT_FOUND_ERROR")

    db.delete(friend_request)
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)