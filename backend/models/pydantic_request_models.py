from datetime import date
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
    password: str = pydantic.Field(max_length = 100)


class SessionModel(pydantic.BaseModel):
    session_id: str = pydantic.Field(max_length = 100)


class UserUpdateModel(pydantic.BaseModel):
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)
    date_of_birth: date | None = pydantic.Field()
    gender: backend.storage.database.Gender | None = pydantic.Field()
    email_address: str = pydantic.EmailStr()
    phone_number: str | None = pydantic.Field(pattern = r"^\+\d{10,15}$")
    country: str | None = pydantic.Field(max_length = 100)
    city: str | None = pydantic.Field(max_length = 100)
    about: str | None = pydantic.Field(max_length = 5000)


class UserUpdateLoginModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)


class UserUpdatePasswordModel(pydantic.BaseModel):
    old_password: str = pydantic.Field(max_length = 100)
    password: str = pydantic.Field(max_length = 100)


class IDModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)


class OffsetMultiplierModel(pydantic.BaseModel):
    offset_multiplier: int = pydantic.Field(ge = 0, default = 0)


class UserUsernameOffsetModel(OffsetMultiplierModel):
    username: str = pydantic.Field(max_length = 100)


class UserNamesOffsetModel(OffsetMultiplierModel):
    name: str | None = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)