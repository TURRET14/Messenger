import pydantic

class MessageModel(pydantic.BaseModel):
    message_text: str | None = pydantic.Field()