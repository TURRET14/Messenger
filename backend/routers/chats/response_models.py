import pydantic
import datetime

import backend.storage

class ChatResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_kind: backend.storage.ChatKind = pydantic.Field()
    name: str = pydantic.Field()
    owner_user_id: int | None = pydantic.Field()
    date_and_time_created: datetime.datetime = pydantic.Field()


class ChatMembershipResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    chat_user_id: int = pydantic.Field()
    date_and_time_added: datetime.datetime = pydantic.Field()
    chat_role: backend.storage.ChatRole = pydantic.Field()