import argon2
import fastapi


password_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    try:
        return password_hasher.hash(password)
    except argon2.exceptions.HashingError:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR, detail = "HASHING_ERROR")


def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except argon2.exceptions.VerifyMismatchError:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_PASSWORD_ERROR")
    except argon2.exceptions.VerificationError:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_PASSWORD_ERROR")
    except argon2.exceptions.InvalidHashError:
        raise fastapi.exceptions.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "INCORRECT_PASSWORD_ERROR")