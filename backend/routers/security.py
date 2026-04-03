import argon2
import fastapi
from backend.routers.errors import (ErrorRegistry)


password_hasher = argon2.PasswordHasher()


async def hash_password(password: str) -> str:
    return password_hasher.hash(password)


async def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except argon2.exceptions.VerifyMismatchError | argon2.exceptions.VerificationError | argon2.exceptions.InvalidHashError:
        return False