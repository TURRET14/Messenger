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


    class Config:
        orm_mode = True

class MessageDeleteModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)