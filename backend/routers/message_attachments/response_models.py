import pydantic

class MessageAttachmentResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    message_id: int = pydantic.Field()
    chat_id: int = pydantic.Field()
    file_extension: str = pydantic.Field(description="Суффикс файла в хранилище, например .png")