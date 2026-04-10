import datetime
import pydantic

from backend.storage import *
from backend.storage.database import Gender as DatabaseGender


class RegisterRequestModel(pydantic.BaseModel):
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length=100)
    second_name: str | None = pydantic.Field(max_length=100)
    email_address: str = pydantic.EmailStr()
    login: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(min_length = 5, max_length = 100)


class EmailRequestModel(pydantic.BaseModel):
    email_address: str = pydantic.EmailStr()


class LoginRequestModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(min_length = 5, max_length = 100)


class SessionRequestModel(pydantic.BaseModel):
    session_id: str = pydantic.Field(max_length = 100)


class UserUpdateRequestModel(pydantic.BaseModel):
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)
    date_of_birth: datetime.date | None = pydantic.Field()
    gender: Gender | None = pydantic.Field()
    email_address: str = pydantic.EmailStr()
    phone_number: str | None = pydantic.Field(pattern = r"^\+\d{10,15}$")
    about: str | None = pydantic.Field(max_length = 5000)

    @pydantic.field_validator("date_of_birth")
    @classmethod
    def date_validator(cls, v):
        if not v:
            return v

        if v > datetime.date.today():
            raise ValueError("INCORRECT_DATE_OF_BIRTH_ERROR")
        else:
            return v


class UserUpdateLoginRequestModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)


class UserUpdatePasswordRequestModel(pydantic.BaseModel):
    old_password: str = pydantic.Field(max_length = 100)
    new_password: str = pydantic.Field(min_length = 5, max_length = 100)


class CodeModel(pydantic.BaseModel):
    code: str = pydantic.Field(max_length = 100)


UserUpdateRequestModel.model_rebuild(_types_namespace={"Gender": DatabaseGender})
