from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import auth, export_logs, features, plants

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
_MEDIA_ROOT = (BASE_DIR / settings.plant_media_subdir).resolve()
_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="中国植物库管理 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/api/media/plants",
    StaticFiles(directory=str(_MEDIA_ROOT)),
    name="plant_media",
)

app.include_router(auth.router, prefix="/api")
app.include_router(plants.router, prefix="/api")
app.include_router(export_logs.router, prefix="/api")
app.include_router(features.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
