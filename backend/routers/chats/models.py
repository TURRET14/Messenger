import pydantic
import datetime

import sqlalchemy
from backend.routers.common_models import *

import backend.storage

class GroupChatModel(pydantic.BaseModel):
    name: str | None = pydantic.Field(max_length = 100)


class ChatResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_kind: backend.storage.ChatKind = pydantic.Field()
    name: str = pydantic.Field(max_length = 100)
    owner_user_id: int | None = pydantic.Field(ge = 0)
    date_and_time_created: datetime.datetime = pydantic.Field()
    is_read_only: bool = pydantic.Field()

    class Config:
        orm_mode = True


class ChatUserModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    username: str = pydantic.Field(max_length=100)
    name: str = pydantic.Field(max_length=100)
    surname: str | None = pydantic.Field(max_length=100)
    second_name: str | None = pydantic.Field(max_length=100)
    date_and_time_added: datetime.datetime = pydantic.Field()
    chat_role: backend.storage.ChatRole = pydantic.Field()

    class Config:
        orm_mode = True


class ChatWithReceiversModel(pydantic.BaseModel):
    chat_id: int = pydantic.Field(ge = 0)
    receivers: list[int] = pydantic.Field()
    is_avatar_changed: bool = pydantic.Field()
    class Config:
        orm_mode = True


class ChatUserWithReceiversModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    receivers: list[int] = pydantic.Field()


class ChatIDModelWithAvatarData(IDModel):
    is_avatar_changed: bool = pydantic.Field()