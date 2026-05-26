import os
import fastapi
import fastapi.middleware.cors
import sqlalchemy.exc
import uvicorn
from backend.routers.errors import ErrorRegistry
import backend.routers.users.router
import backend.routers.chats.router
import backend.routers.chats.websockets.websockets
import backend.routers.chats.websockets.listeners.router
import backend.routers.messages.router
import backend.routers.message_attachments.router
import backend.routers.messages.websockets.websockets
import backend.routers.messages.websockets.listeners.router
import backend.environment as environment
import contextlib
from backend.storage import database

@contextlib.asynccontextmanager
async def on_startup(app):
    await database.init_db()
    yield

app = fastapi.FastAPI(lifespan = on_startup)

app.add_middleware(fastapi.middleware.cors.CORSMiddleware,
                allow_origins = environment.FRONTEND_ORIGINS,
                allow_credentials = True,
                allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"],
                allow_headers = ["*"])


app.include_router(backend.routers.users.router.users_router)

app.include_router(backend.routers.chats.router.chats_router)
app.include_router(backend.routers.chats.websockets.websockets.chats_websockets)
app.include_router(backend.routers.chats.websockets.listeners.router.chats_websocket_listener_router )

app.include_router(backend.routers.messages.router.messages_router)
app.include_router(backend.routers.messages.websockets.websockets.messages_websockets_router)
app.include_router(backend.routers.messages.websockets.listeners.router.messages_websocket_listener_router)

app.include_router(backend.routers.message_attachments.router.message_attachments_router)


@app.exception_handler(fastapi.exceptions.HTTPException)
async def http_exception_handler(request: fastapi.requests.Request, exception: fastapi.exceptions.HTTPException):
    return fastapi.responses.JSONResponse(
        fastapi.encoders.jsonable_encoder(exception.detail),
        status_code = exception.status_code)


@app.exception_handler(sqlalchemy.exc.IntegrityError)
async def integrity_error_handler(request: fastapi.requests.Request, exception: sqlalchemy.exc.IntegrityError):
    # Гонки уникальных ограничений (например, два параллельных создания
    # пользователя с одним username/login) превращаем в осмысленный 409
    # вместо сырого 500 с трейсбэком.
    return fastapi.responses.JSONResponse(
        fastapi.encoders.jsonable_encoder(ErrorRegistry.data_conflict_error),
        status_code = ErrorRegistry.data_conflict_error.error_status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: fastapi.requests.Request, exception: Exception):
    # Любая необработанная ошибка отдаётся как обобщённый 500 без утечки
    # трейсбэка/внутренних деталей наружу.
    return fastapi.responses.JSONResponse(
        fastapi.encoders.jsonable_encoder(ErrorRegistry.internal_server_error),
        status_code = ErrorRegistry.internal_server_error.error_status_code)


if __name__ == "__main__":
    uvicorn.run(app, host = "0.0.0.0", port = int(environment.BACKEND_PORT))
