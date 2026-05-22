import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent
_PLANT_ADMIN_DIR = _BACKEND_DIR.parent
_ROOT_DIR = _PLANT_ADMIN_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            _ROOT_DIR / ".env",
            _PLANT_ADMIN_DIR / ".env",
            _BACKEND_DIR / ".env",
            Path(".env")
        ),
        extra="ignore"
    )

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "plant"
    db_charset: str = "utf8mb4"

    database_url: str | None = None
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    # 网页自助注册：生产环境建议 REGISTER_ENABLED=false，且勿开放 REGISTER_ALLOW_ADMIN
    register_enabled: bool = True
    register_allow_admin: bool = False
    # 物种图片缓存目录（相对 backend 项目根），挂载为 /api/media/plants
    plant_media_subdir: str = "data/plant_images"


@lru_cache
def get_settings() -> Settings:
    return Settings()

