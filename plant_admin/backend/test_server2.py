"""测试同步路由 + StaticFiles + CORS 哪个导致挂起"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MEDIA = Path(__file__).parent / "data" / "plant_images"
_MEDIA.mkdir(parents=True, exist_ok=True)
app.mount("/api/media/plants", StaticFiles(directory=str(_MEDIA)), name="plant_media")

@app.get("/api/health")
def health():          # 同步 def，和主应用一致
    return {"status": "ok"}
