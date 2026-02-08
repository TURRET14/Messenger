import pydantic
import backend.storage.database
import datetime

class UserInListModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)

    class Config:
        orm_mode = True


class FriendRequestUserInListModel(UserInListModel):
    friend_request_id: int = pydantic.Field(ge = 0)
    date_and_time_sent: datetime.datetime = pydantic.Field()

    class Config:
        orm_mode = True


class UserModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    username: str = pydantic.Field(max_length = 100)
    name: str = pydantic.Field(max_length = 100)
    surname: str | None = pydantic.Field(max_length = 100)
    second_name: str | None = pydantic.Field(max_length = 100)
    date_of_birth: datetime.date | None = pydantic.Field()
    gender: backend.storage.database.Gender | None = pydantic.Field()
    email_address: str = pydantic.Field(max_length = 260)
    phone_number: str | None = pydantic.Field(pattern = r"^\+\d{10,15}$")
    country: str | None = pydantic.Field(max_length = 100)
    city: str | None = pydantic.Field(max_length = 100)
    about: str | None = pydantic.Field(max_length = 5000)
    date_and_time_registered: datetime.datetime = pydantic.Field()
    messenger_role: backend.storage.database.SystemRoles = pydantic.Field()

    class Config:
        orm_mode = True


class UserLoginModel(pydantic.BaseModel):
    login: str = pydantic.Field(max_length = 100)

    class Config:
        orm_mode = True


class ChatModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    is_group_chat: bool = pydantic.Field()
    name: str = pydantic.Field(max_length = 100)
    owner_user_id: int = pydantic.Field(ge = 0)
    date_and_time_created: datetime.datetime = pydantic.Field()

    class Config:
        orm_mode = True


class ChatUserModel(UserInListModel):
    is_user_admin: bool = pydantic.Field()

    class Config:
        orm_mode = True


class MessageModel(pydantic.BaseModel):
    id: int = pydantic.Field(ge = 0)
    chat_id: int = pydantic.Field(ge = 0)
    date_and_time_sent: datetime.datetime = pydantic.Field()
    message_text: str | None = pydantic.Field()
    sender_user: UserInListModel

    class Config:
        orm_mode = True