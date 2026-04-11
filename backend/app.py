import os
import fastapi
import fastapi.middleware.cors
import uvicorn
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


if __name__ == "__main__":
    uvicorn.run(app, host = "0.0.0.0", port = int(environment.BACKEND_PORT))
