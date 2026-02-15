import enum

success_return_message: dict = {"success": True}

class ExceptionDetails(enum.Enum):
    user_not_found_error = "USER_NOT_FOUND_ERROR"
    object_not_found_error = "OBJECT_NOT_FOUND_ERROR"
    chat_not_found_error = "CHAT_NOT_FOUND_ERROR"
    message_not_found_error = "MESSAGE_NOT_FOUND_ERROR"

    object_already_exists_error = "OBJECT_ALREADY_EXISTS_ERROR"
    chat_already_exists_error = "CHAT_ALREADY_EXISTS_ERROR"

    unauthorized_error = "UNAUTHORIZED_ERROR"
    forbidden_error = "FORBIDDEN_ERROR"
    bad_request_error = "BAD_REQUEST_ERROR"
    conflict_error = "CONFLICT_ERROR"

    incorrect_login_error = "INCORRECT_LOGIN_ERROR"
    incorrect_password_error = "INCORRECT_PASSWORD_ERROR"
    invalid_session_id_error = "INCORRECT_SESSION_ID_ERROR"

    login_already_taken_error = "LOGIN_ALREADY_TAKEN_ERROR"
    username_already_taken_error = "USERNAME_ALREADY_TAKEN_ERROR"
    email_already_taken_error = "EMAIL_ALREADY_TAKEN_ERROR"
    phone_number_already_taken_error = "PHONE_NUMBER_ALREADY_TAKEN_ERROR"

    image_type_not_allowed_error = "IMAGE_TYPE_NOT_ALLOWED_ERROR"
    image_size_too_large_error = "IMAGE_SIZE_TOO_LARGE_ERROR"