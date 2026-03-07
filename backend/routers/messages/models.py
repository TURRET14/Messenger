import pydantic
import datetime

class MessageModel(pydantic.BaseModel):
    message_text: str | None = pydantic.Field()
    reply_message_id: int | None = pydantic.Field(ge = 0)


class MessageResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    date_and_time_sent: datetime.datetime = pydantic.Field()
    date_and_time_edited: datetime.datetime = pydantic.Field()
    message_text: str | None = pydantic.Field()
    sender_id: int = pydantic.Field(ge = 0)
    sender_username: str = pydantic.Field(max_length = 100)
    sender_name: str = pydantic.Field(max_length = 100)
    sender_surname: str | None = pydantic.Field(max_length = 100)
    sender_second_name: str | None = pydantic.Field(max_length = 100)
    reply_message_id: int | None = pydantic.Field(ge = 0)
    is_read: bool = pydantic.Field(default = False)


    class Config:
        orm_mode = True

class MessageIDWithChatIDModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)

class MessageIDWithChatIDWithReceiversModel(MessageIDWithChatIDModel):
    receivers: list[int] = pydantic.Field()

class ReadMarkData(MessageIDWithChatIDWithReceiversModel):
    message_id: int = pydantic.Field(ge = 0)
    reader_id: int = pydantic.Field(ge = 0)


class MessageReadMarkResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    message_id: int = pydantic.Field(ge = 0)
    reader_id: int = pydantic.Field(ge = 0)