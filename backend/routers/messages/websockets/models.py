import datetime
import pydantic


class MessagePubsubWebsocketModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    date_and_time_sent: datetime.datetime = pydantic.Field()
    date_and_time_edited: datetime.datetime = pydantic.Field()
    message_text: str = pydantic.Field()
    is_read: bool = pydantic.Field()

class ReadMarkPubsubWebsocketModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    message_id: int = pydantic.Field()
    reader_user_id: int = pydantic.Field()