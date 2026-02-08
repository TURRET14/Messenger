import datetime
import pydantic

import backend.storage.database


class RegisterModel(pydantic.BaseModel):
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    email_address: str = pydantic.EmailStr()
    login: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(min_length = 10, max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)


class LoginModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(min_length = 10, max_length = 100)


class SessionModel(pydantic.BaseModel):
    session_id: str = pydantic.Field(max_length = 100)


class UserUpdateModel(pydantic.BaseModel):
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)
    date_of_birth: datetime.date | None = pydantic.Field()
    gender: backend.storage.database.Gender | None = pydantic.Field()
    email_address: str = pydantic.EmailStr()
    phone_number: str | None = pydantic.Field(pattern = r"^\+\d{10,15}$")
    country: str | None = pydantic.Field(max_length = 100)
    city: str | None = pydantic.Field(max_length = 100)
    about: str | None = pydantic.Field(max_length = 5000)

    @pydantic.field_validator("date_of_birth")
    @classmethod
    def date_validator(cls, v):
        if v is None:
            return v

        if v > datetime.date.today():
            raise ValueError("INCORRECT_DATE_OF_BIRTH_ERROR")
        else:
            return v


class UserUpdateLoginModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)


class UserUpdatePasswordModel(pydantic.BaseModel):
    old_password: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(min_length = 10, max_length = 100)


class IDModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)


class GroupChatModel(pydantic.BaseModel):
    name: str | None = pydantic.Field(max_length = 100)


class MessageModel(pydantic.BaseModel):
    message_text: str | None = pydantic.Field()