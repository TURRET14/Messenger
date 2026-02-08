import fastapi
import sqlalchemy.orm
import minio
from psycopg.types.range import fail_dump

import backend.handles.implementations.messages
import backend.authorization.sessions
import backend.models.pydantic_request_models
import backend.models.pydantic_response_models
import backend.storage.minio
import backend.storage.database
import backend.storage.redis

messages_router = fastapi.APIRouter()

@messages_router.get("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse, response_model=backend.models.pydantic_response_models.MessageModel)
async def get_chat_messages(
    chat_id: int = fastapi.Path(ge = 0),
    offset_multiplier: int = fastapi.Query(default = 0, ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.messages.get_chat_messages(chat_id, offset_multiplier, current_user, db)


@messages_router.post("/chats/id/{chat_id}/messages", response_class = fastapi.responses.JSONResponse)
async def post_message(
    chat_id: int = fastapi.Path(ge = 0),
    data: backend.models.pydantic_request_models.MessageModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.messages.post_message(chat_id, data, current_user, db)


@messages_router.delete("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.JSONResponse)
async def delete_message(
    chat_id: int = fastapi.Path(ge = 0),
    message_id: int = fastapi.Path(ge = 0),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.messages.post_message(chat_id, message_id, current_user, db)

@messages_router.put("/chats/id/{chat_id}/messages/id/{message_id}", response_class = fastapi.responses.JSONResponse)
async def update_message(
    chat_id: int = fastapi.Path(ge = 0),
    message_id: int = fastapi.Path(ge = 0),
    data: backend.models.pydantic_request_models.MessageModel = fastapi.Body(),
    current_user: backend.storage.database.User = fastapi.Depends(backend.authorization.sessions.get_session_user),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.messages.update_message(chat_id, message_id, data, current_user, db)