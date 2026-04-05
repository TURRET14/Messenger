import pydantic
import datetime
from backend.storage import *


class ChatPubsubModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_kind: ChatKind = pydantic.Field()
    name: str = pydantic.Field()
    owner_user_id: int = pydantic.Field()
    date_and_time_created: datetime.datetime = pydantic.Field()
    is_avatar_changed: bool = pydantic.Field()


class ChatWithReceiversPubsubDeleteModel(ChatPubsubModel):
    receivers: list[int] = pydantic.Field()


class ChatMembershipPubsubModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_user_id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    date_and_time_added: datetime.datetime = pydantic.Field()
    chat_role: ChatRole = pydantic.Field()