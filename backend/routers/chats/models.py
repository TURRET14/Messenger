import pydantic

class GroupChatModel(pydantic.BaseModel):
    name: str | None = pydantic.Field(max_length = 100)