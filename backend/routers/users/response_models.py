import datetime
import pydantic

from backend.storage import *


class UserInListResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    username: str = pydantic.Field()
    name: str = pydantic.Field()
    surname: str | None = pydantic.Field()
    second_name: str | None = pydantic.Field()


class FriendUserInListResponseModel(UserInListResponseModel):
    date_and_time_added: datetime.datetime = pydantic.Field()


class FriendRequestResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    sender_user_id: int = pydantic.Field()
    receiver_user_id: int = pydantic.Field()
    date_and_time_sent: datetime.datetime = pydantic.Field()


class UserResponseModel(pydantic.BaseModel):
    id: int = pydantic.Field()
    username: str = pydantic.Field()
    name: str = pydantic.Field()
    surname: str | None = pydantic.Field()
    second_name: str | None = pydantic.Field()
    date_of_birth: datetime.date | None = pydantic.Field()
    gender: Gender | None = pydantic.Field()
    phone_number: str | None = pydantic.Field()
    about: str | None = pydantic.Field()
    date_and_time_registered: datetime.datetime = pydantic.Field()


class CurrentUserResponseModel(UserResponseModel):
    email_address: str = pydantic.Field()

class LoginResponseModel(pydantic.BaseModel):
    login: str = pydantic.Field()


class SessionResponseModel(pydantic.BaseModel):
    session_id: str = pydantic.Field()
    user_id: int = pydantic.Field()
    user_agent: str = pydantic.Field()
    creation_datetime: int = pydantic.Field()
    expiration_datetime: int = pydantic.Field()