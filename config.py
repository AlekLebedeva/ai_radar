from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_radar"
    debug: bool = True
    admin_static_path: str = "static/admin"
    parser_interval_hours: int = 48

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
