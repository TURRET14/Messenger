import pydantic

class MessageRequestModel(pydantic.BaseModel):
    message_text: str | None = pydantic.Field()

class MessagePostRequestModel(MessageRequestModel):
    message_text: str | None = pydantic.Field()
    reply_message_id: int | None = pydantic.Field(ge = 0)
    parent_message_id: int | None = pydantic.Field(ge = 0)