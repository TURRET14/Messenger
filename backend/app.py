import os
import fastapi
import fastapi.middleware.cors
import uvicorn
import backend.routers.users.router
import backend.routers.chats.router
import backend.routers.messages.router
import backend.routers.message_attachments.router
import backend.routers.messages.websockets
import backend.routers.message_attachments.websockets
import backend.routers.chats.websockets
import backend.routers.chats.websocket_listeners_router
import backend.routers.messages.websocket_listeners_router
import backend.routers.message_attachments.websocket_listeners_router
import dotenv

dotenv.load_dotenv()

app = fastapi.FastAPI()
app.add_middleware(fastapi.middleware.cors.CORSMiddleware,
                allow_origins = [os.getenv("FRONTEND_URL")],
                allow_credentials = True,
                allow_methods = ["GET", "POST", "PUT", "DELETE"],
                allow_headers = ["session_id"],
                expose_headers = ["session_id"])

app.include_router(backend.routers.users.router.users_router)

app.include_router(backend.routers.chats.router.chats_router)
app.include_router(backend.routers.chats.websockets.chats_websockets)
app.include_router(backend.routers.chats.websocket_listeners_router.chats_websocket_listener_router)

app.include_router(backend.routers.messages.router.messages_router)
app.include_router(backend.routers.messages.websockets.messages_websockets)
app.include_router(backend.routers.messages.websocket_listeners_router.messages_websocket_router)

app.include_router(backend.routers.message_attachments.router.message_attachments_router)
app.include_router(backend.routers.message_attachments.websockets.message_attachments_websockets)
app.include_router(backend.routers.message_attachments.websocket_listeners_router.message_attachments_router)




@app.exception_handler(fastapi.exceptions.HTTPException)
async def http_exception_handler(request: fastapi.requests.Request, exception: fastapi.exceptions.HTTPException):
    return fastapi.responses.JSONResponse(exception.detail, status_code=exception.status_code)


uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)