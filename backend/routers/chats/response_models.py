import pydantic
import datetime

import backend.storage


class ChatLastMessagePreviewModel(pydantic.BaseModel):
    message_text: str | None = pydantic.Field(default=None)
    sender_user_id: int | None = pydantic.Field(default=None)
    date_and_time_sent: datetime.datetime | None = pydantic.Field(default=None)


class ChatResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_kind: backend.storage.ChatKind = pydantic.Field()
    name: str = pydantic.Field()
    owner_user_id: int | None = pydantic.Field()
    date_and_time_created: datetime.datetime = pydantic.Field()
    has_avatar: bool = pydantic.Field(default=False)
    last_message: ChatLastMessagePreviewModel | None = pydantic.Field(default=None)


class ChatMembershipResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    chat_user_id: int = pydantic.Field()
    date_and_time_added: datetime.datetime = pydantic.Field()
    chat_role: backend.storage.ChatRole = pydantic.Field()