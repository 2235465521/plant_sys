from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/plant?charset=utf8mb4"
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
