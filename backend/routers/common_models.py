import pydantic

class IDModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)