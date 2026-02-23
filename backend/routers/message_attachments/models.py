import pydantic
from backend.storage import *

class MessageAttachmentModel(pydantic.BaseModel):
    message_attachment_id: int = pydantic.Field(ge = 0)
    message_id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)