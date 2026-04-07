import datetime
import pydantic


class MessagePubsubWebsocketModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    sender_user_id: int | None = pydantic.Field()
    date_and_time_sent: datetime.datetime = pydantic.Field()
    date_and_time_edited: datetime.datetime | None = pydantic.Field()
    message_text: str | None = pydantic.Field()
    parent_message_id: int | None = pydantic.Field()
    reply_message_id: int | None = pydantic.Field()
    is_read: bool | None = pydantic.Field()
    receivers: list[int] = pydantic.Field()


class LastMessagePubsubWebsocketModel(pydantic.BaseModel):
    message: MessagePubsubWebsocketModel | None = pydantic.Field()
    chat_id: int = pydantic.Field()
    receivers: list[int] = pydantic.Field()

class ReadMarkPubsubWebsocketModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    message_id: int = pydantic.Field()
    reader_user_id: int = pydantic.Field()
    date_and_time_received: datetime.datetime = pydantic.Field()
    receivers: list[int] = pydantic.Field()