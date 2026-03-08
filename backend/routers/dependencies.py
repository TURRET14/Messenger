from datetime import datetime

import fastapi
import redis.asyncio
import sqlalchemy
import sqlalchemy.orm

from backend.routers.common_models import *
from backend.storage import *
import backend.routers.return_details


async def get_session_user(
    session_id: str = fastapi.Cookie(),
    db: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    redis_client: redis.asyncio.Redis = fastapi.Depends(redis_handler.get_redis_client)) -> User:

    session: dict[str, str] | None = await redis_client.hgetall(f"session_id:{session_id}")
    if session:
        if int(session["expiration_date"]) > int(datetime.now().timestamp()):
            session_user = db.execute(sqlalchemy.select(User).where(User.id == session["user_id"])).scalars().first()
            if session_user:
                return session_user
            else:
                raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INVALID_SESSION_ID_ERROR)
        else:
            raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INVALID_SESSION_ID_ERROR)
    else:
        raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = backend.routers.return_details.INVALID_SESSION_ID_ERROR)


async def get_user_by_path_user_id(
    user_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.Session = fastapi.Depends(database.get_db)) -> User:

    selected_user: User = db.execute(sqlalchemy.select(User).where(User.id == user_id)).scalars().first()

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.USER_NOT_FOUND_ERROR)
    else:
        return selected_user


async def get_user_by_data_id(
    user_id_model: IDModel = fastapi.Body(),
    db: sqlalchemy.orm.Session = fastapi.Depends(database.get_db)) -> User:

    selected_user: User = db.execute(sqlalchemy.select(User).where(User.id == user_id_model.id)).scalars().first()

    if not selected_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.USER_NOT_FOUND_ERROR)
    else:
        return selected_user


async def get_chat_by_path_id(
    chat_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.Session = fastapi.Depends(database.get_db)) -> Chat:

    selected_chat: Chat = db.execute(sqlalchemy.select(Chat).where(Chat.id == chat_id)).scalars().first()

    if not selected_chat:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.CHAT_NOT_FOUND_ERROR)
    else:
        return selected_chat


async def get_message_by_path_id(
    message_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.Session = fastapi.Depends(database.get_db)) -> Message:

    selected_message: Message = db.execute(sqlalchemy.select(Message).where(Message.id == message_id)).scalars().first()

    if not selected_message:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.MESSAGE_NOT_FOUND_ERROR)
    else:
        return selected_message


async def get_message_attachment_by_id(
    attachment_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> FileAttachment:

    selected_attachment: FileAttachment = db.execute(sqlalchemy.select(FileAttachment).where(FileAttachment.id == attachment_id)).scalars().first()

    if not selected_attachment:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)
    else:
        return selected_attachment


async def get_chat_user_by_path_id(
    chat_user_id: int = fastapi.Path(ge = 0),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(database.get_db)) -> ChatUser:

    chat_user: ChatUser = db.execute(sqlalchemy.select(ChatUser).where(ChatUser.id == chat_user_id)).scalars().first()

    if not chat_user:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_404_NOT_FOUND, detail = backend.routers.return_details.OBJECT_NOT_FOUND_ERROR)
    else:
        return chat_user