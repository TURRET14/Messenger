import fastapi
import sqlalchemy.orm

import backend.models.pydantic_request_models
import backend.storage.database
import backend.authorization.password_hashing
import backend.handles.implementations.authorization
import backend.storage.redis


authorization_router = fastapi.APIRouter()


@authorization_router.post("/register", response_class=fastapi.responses.JSONResponse)
async def post_register(
    data: backend.models.pydantic_request_models.RegisterModel = fastapi.Body(),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db())) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.authorization.post_register(data, db)


@authorization_router.post("/login", response_class=fastapi.responses.JSONResponse)
async def post_login(
    data: backend.models.pydantic_request_models.LoginModel = fastapi.Body(),
    response: fastapi.responses.Response = fastapi.responses.Response(),
    db: sqlalchemy.orm.session.Session = fastapi.Depends(backend.storage.database.get_db()),
    redis_client: backend.storage.redis.RedisClient = fastapi.Depends(backend.storage.redis.get_redis_client)) -> fastapi.responses.JSONResponse:

    return await backend.handles.implementations.authorization.post_login(data, response, db, redis_client)