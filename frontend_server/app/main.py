import os
from pathlib import Path

import fastapi
import fastapi.responses
import fastapi.staticfiles

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


def _safe_file(full_path: str) -> Path | None:
    if not full_path:
        return None
    parts = Path(full_path).parts
    if ".." in parts:
        return None
    candidate = (STATIC_DIR / full_path).resolve()
    try:
        candidate.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


app = fastapi.FastAPI(title="Messenger static frontend", version="1.0.0")

assets_dir = STATIC_DIR / "assets"
if assets_dir.is_dir():
    app.mount(
        "/assets",
        fastapi.staticfiles.StaticFiles(directory=assets_dir),
        name="assets",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> fastapi.responses.Response:
    return fastapi.responses.Response(status_code=404)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str) -> fastapi.responses.FileResponse:
    if full_path.startswith("api/"):
        raise fastapi.HTTPException(status_code=404)
    file_path = _safe_file(full_path)
    if file_path is not None:
        return fastapi.responses.FileResponse(path=str(file_path))
    if INDEX_FILE.is_file():
        return fastapi.responses.FileResponse(path=str(INDEX_FILE))
    raise fastapi.HTTPException(
        status_code=503,
        detail="Статика фронтенда не собрана (нет index.html).",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("FRONTEND_STATIC_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
