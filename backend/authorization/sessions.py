import fastapi
import redis
import sqlalchemy
import sqlalchemy.orm
import backend.storage.redis
import backend.storage.database
from datetime import datetime

async def get_session_user(
    session_id: str = fastapi.Cookie(),
    db: sqlalchemy.orm.Session = fastapi.Depends(backend.storage.database.get_db),
    redis_client: redis.Redis = fastapi.Depends(backend.storage.redis.get_redis_client)) -> backend.storage.database.User:

    session: dict[str, str] | None = await redis_client.hgetall(f"session_id:{session_id}")
    if session is not None:
        if int(session["expiration_date"]) > int(datetime.now().timestamp()):
            session_user = db.execute(sqlalchemy.select(backend.storage.database.User).where(backend.storage.database.User.id == session["user_id"])).scalar()
            if session_user is not None:
                return session_user
            else:
                raise fastapi.HTTPException(status_code = fastapi.status.HTTP_401_UNAUTHORIZED, detail = "SESSION_EXPIRED_OR_INVALID_ERROR")
        else:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="SESSION_EXPIRED_OR_INVALID_ERROR")
    else:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="SESSION_EXPIRED_OR_INVALID_ERROR")