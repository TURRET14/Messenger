import datetime

import fastapi
import sqlalchemy.orm

import backend.dependencies
import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.minio_handler
import backend.storage.database
import backend.storage.redis_handler
import backend.parameters


async def get_chat_messages(
    chat_id: int,
    offset_multiplier: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

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

    messages_list = db.execute(sqlalchemy.select(
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
    .offset(offset_multiplier * backend.parameters.number_of_table_entries_in_selection)
    .limit(backend.parameters.number_of_table_entries_in_selection)).scalars().all()

    return fastapi.responses.JSONResponse(messages_list, status_code = fastapi.status.HTTP_200_OK)


async def post_message(
    chat_id: int,
    data: backend.models.pydantic_request_models.MessageModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

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

    new_message: backend.storage.database.Message = backend.storage.database.Message(chat_id = chat_id, sender_user_id = selected_user.id, date_and_time_sent = datetime.datetime.now(datetime.timezone.utc),  message_text = data.message_text)

    db.add(new_message)
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)


async def delete_message(
    chat_id: int,
    message_id: int,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session) -> fastapi.responses.JSONResponse:

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

    message: backend.storage.database.Message = db.execute(sqlalchemy.select(backend.storage.database.Message).where(backend.storage.database.Message.id == message_id)).scalars().first()

    if not message:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "MESSAGE_DOES_NOT_EXISTS_ERROR")

    if message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="MESSAGE_WAS_NOT_WRITTEN_BY_THE_USER_ERROR")

    if message.chat_id != chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail="MESSAGE_DOES_NOT_CORRESPOND_TO_THE_SELECTED_CHAT_ERROR")

    db.delete(message)
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)


async def update_message(
    chat_id: int,
    message_id: int,
    data: backend.models.pydantic_request_models.MessageModel,
    selected_user: backend.storage.database.User,
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

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

    message: backend.storage.database.Message = db.execute(sqlalchemy.select(backend.storage.database.Message).where(backend.storage.database.Message.id == message_id)).scalars().first()

    if not message:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail = "MESSAGE_DOES_NOT_EXISTS_ERROR")

    if message.sender_user_id != selected_user.id:
        raise fastapi.exceptions.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="MESSAGE_WAS_NOT_WRITTEN_BY_THE_USER_ERROR")

    if message.chat_id != chat.id:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_400_BAD_REQUEST, detail="MESSAGE_DOES_NOT_CORRESPOND_TO_THE_SELECTED_CHAT_ERROR")

    message.message_text = data.message_text
    db.commit()

    return fastapi.responses.JSONResponse("SUCCESS", status_code=fastapi.status.HTTP_200_OK)