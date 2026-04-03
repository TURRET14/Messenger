import pydantic

class MessageAttachmentModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    message_id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)

class MessageAttachmentModelWithReceivers(MessageAttachmentModel):
    receivers: list[int] = pydantic.Field()