import pydantic

class ChatNameRequestModel(pydantic.BaseModel):
    name: str = pydantic.Field(max_length = 100)