import enum
import dataclasses

import fastapi

@dataclasses.dataclass()
class ErrorInfo:
    error_code: Error
    error_message: str
    error_status_code: int

class Error(enum.Enum):
    login_already_taken_error = "LOGIN_ALREADY_TAKEN_ERROR"
    username_already_taken_error = "USERNAME_ALREADY_TAKEN_ERROR"
    email_already_taken_error = "EMAIL_ALREADY_TAKEN_ERROR"
    phone_number_already_taken_error = "PHONE_NUMBER_ALREADY_TAKEN_ERROR"
    data_conflict_error = "DATA_CONFLICT_ERROR"
    incorrect_login_error = "INCORRECT_LOGIN_ERROR"
    incorrect_password_error = "INCORRECT_PASSWORD_ERROR"
    invalid_session_error = "SESSION_NOT_FOUND_ERROR"
    unauthorized_error = "UNAUTHORIZED_ERROR"
    forbidden_error = "FORBIDDEN_ERROR"
    file_type_not_allowed_error = "IMAGE_TYPE_NOT_ALLOWED_ERROR"
    file_size_too_large_error = "IMAGE_SIZE_TOO_LARGE_ERROR"
    parameters_were_not_provided_error = "PARAMETERS_WERE_NOT_PROVIDED_ERROR"
    bad_request_error = "BAD_REQUEST_ERROR"
    friend_request_already_exists_error = "FRIEND_REQUEST_ALREADY_EXISTS_ERROR"
    users_are_already_friends_error = "USERS_ARE_ALREADY_FRIENDS_ERROR"
    user_is_blocked_error = "USER_IS_BLOCKED_ERROR"
    friend_request_not_found_error = "FRIEND_REQUEST_NOT_FOUND_ERROR"
    friendship_not_found_error = "FRIENDSHIP_NOT_FOUND_ERROR"
    user_block_not_found_error = "USER_BLOCK_NOT_FOUND_ERROR"
    user_not_found_error = "USER_NOT_FOUND_ERROR"
    chat_not_found_error = "CHAT_NOT_FOUND_ERROR"
    message_not_found_error = "MESSAGE_NOT_FOUND_ERROR"
    message_attachment_not_found_error = "MESSAGE_ATTACHMENT_NOT_FOUND_ERROR"
    chat_membership_not_found_error = "CHAT_MEMBERSHIP_NOT_FOUND_ERROR"


class ErrorRegistry:
    login_already_taken_error = ErrorInfo(error_code = Error.login_already_taken_error, error_message = "Логин уже занят!", error_status_code = fastapi.status.HTTP_409_CONFLICT)
    username_already_taken_error = ErrorInfo(error_code = Error.username_already_taken_error, error_message = "Имя пользователя уже занято!", error_status_code = fastapi.status.HTTP_409_CONFLICT)
    email_already_taken_error = ErrorInfo(error_code = Error.email_already_taken_error, error_message = "Адрес электронной почты уже занят!", error_status_code = fastapi.status.HTTP_409_CONFLICT)
    phone_number_already_taken_error = ErrorInfo(error_code = Error.phone_number_already_taken_error, error_message = "Номер телефона уже занят!", error_status_code = fastapi.status.HTTP_409_CONFLICT)
    data_conflict_error = ErrorInfo(error_code = Error.data_conflict_error, error_message = "Произошел конфликт данных!", error_status_code = fastapi.status.HTTP_409_CONFLICT)
    incorrect_login_error = ErrorInfo(error_code = Error.incorrect_login_error, error_message = "Неверный логин!", error_status_code = fastapi.status.HTTP_401_UNAUTHORIZED)
    incorrect_password_error = ErrorInfo(error_code = Error.incorrect_password_error, error_message = "Неверный пароль!", error_status_code = fastapi.status.HTTP_401_UNAUTHORIZED)
    invalid_session_error = ErrorInfo(error_code = Error.invalid_session_error, error_message ="Указанная сессия не найдена!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    unauthorized_error = ErrorInfo(error_code = Error.unauthorized_error, error_message = "Вы не авторизованы!", error_status_code = fastapi.status.HTTP_401_UNAUTHORIZED)
    forbidden_error = ErrorInfo(error_code = Error.forbidden_error, error_message = "Вам не хватает прав!", error_status_code = fastapi.status.HTTP_403_FORBIDDEN)
    file_type_not_allowed_error = ErrorInfo(error_code = Error.file_type_not_allowed_error, error_message = "Этот тип файла не поддерживается!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    file_size_too_large = ErrorInfo(error_code = Error.file_size_too_large_error, error_message = "Размер файла слишком большой!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    parameters_were_not_provided_error = ErrorInfo(error_code = Error.parameters_were_not_provided_error, error_message = "Необходимые параметры запроса не были указаны!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    bad_request_error = ErrorInfo(error_code = Error.bad_request_error, error_message = "Некорректные параметры запроса!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    friend_request_already_exists_error = ErrorInfo(error_code = Error.friend_request_already_exists_error, error_message = "Запрос в друзья уже существует!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    users_are_already_friends_error = ErrorInfo(error_code = Error.users_are_already_friends_error, error_message = "Пользователи уже являются друзьями!", error_status_code = fastapi.status.HTTP_400_BAD_REQUEST)
    user_is_blocked_error = ErrorInfo(error_code = Error.user_is_blocked_error, error_message = "Получатель заблокирован вами или вы заблокированы получателем!", error_status_code = fastapi.status.HTTP_403_FORBIDDEN)
    friend_request_not_found_error = ErrorInfo(error_code = Error.friend_request_not_found_error, error_message = "Запрос в друзья не найден!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    friendship_not_found_error = ErrorInfo(error_code = Error.friendship_not_found_error, error_message = "Дружба не найдена!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    user_block_not_found_error = ErrorInfo(error_code = Error.user_block_not_found_error, error_message = "Блокировка пользователя не найдена!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    user_not_found_error = ErrorInfo(error_code = Error.user_not_found_error, error_message = "Пользователь не найден!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    chat_not_found_error = ErrorInfo(error_code = Error.chat_not_found_error, error_message = "Чат не найден!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    message_not_found_error = ErrorInfo(error_code = Error.message_not_found_error, error_message = "Сообщение не найдено!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    message_attachment_not_found_error = ErrorInfo(error_code = Error.message_attachment_not_found_error, error_message = "Вложение не найдено!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)
    chat_membership_not_found_error = ErrorInfo(error_code = Error.chat_membership_not_found_error, error_message = "Членство в чате не найдено!", error_status_code = fastapi.status.HTTP_404_NOT_FOUND)