import pydantic


class MessageIDWithChatIDWithReceiversModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    receivers: list[int] = pydantic.Field()

class ReadMarkData(MessageIDWithChatIDWithReceiversModel):
    message_id: int = pydantic.Field(ge = 0)
    reader_id: int = pydantic.Field(ge = 0)


class MessageReadMarkResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    message_id: int = pydantic.Field(ge = 0)
    reader_id: int = pydantic.Field(ge = 0)