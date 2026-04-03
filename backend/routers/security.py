import argon2
import fastapi
from backend.routers.errors import (ErrorRegistry)


password_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    try:
        return password_hasher.hash(password)
    except argon2.exceptions.HashingError:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.internal_server_error.error_status_code, detail = ErrorRegistry.internal_server_error)


def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except argon2.exceptions.VerifyMismatchError:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.incorrect_password_error.error_status_code, detail = ErrorRegistry.incorrect_password_error)
    except argon2.exceptions.VerificationError:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.incorrect_password_error.error_status_code, detail = ErrorRegistry.incorrect_password_error)
    except argon2.exceptions.InvalidHashError:
        raise fastapi.exceptions.HTTPException(status_code = ErrorRegistry.incorrect_password_error.error_status_code, detail = ErrorRegistry.incorrect_password_error)