import os
import fastapi
import fastapi.middleware.cors
import uvicorn
import backend.handles.authorization
import dotenv

dotenv.load_dotenv()

app = fastapi.FastAPI()
app.add_middleware(fastapi.middleware.cors.CORSMiddleware,
                allow_origins = [os.getenv("FRONTEND_URL")],
                allow_credentials = True,
                allow_methods = ["GET", "POST", "PUT", "DELETE"],
                allow_headers = ["session_id"],
                expose_headers = ["session_id"])

app.include_router(backend.handles.handles_authorization.authorization_router)


@app.exception_handler(fastapi.exceptions.HTTPException)
async def http_exception_handler(request: fastapi.requests.Request, exception: fastapi.exceptions.HTTPException):
    return fastapi.responses.JSONResponse(exception.detail, status_code=exception.status_code)


uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)