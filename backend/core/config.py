from pydantic_settings import BaseSettings,SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI-LLM-API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "mysql+aiomysql://root:123456@127.0.0.1:3306/demo_fast_api"

    # JWT
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 3000

    # CORS
    # ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    model_config = SettingsConfigDict(env_file=".env")
    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()