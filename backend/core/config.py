from xml.parsers.expat import model

from pydantic_settings import BaseSettings,SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "LLM BACKEND"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = ""

    # LLM Provider
    LLM_PROVIDER: str = "cloudflare"  # Options: "cloudflare", "ollama"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "your-local-model"

    # Cloudflare
    CF_ACCOUNT_ID: str = ""
    CF_API_TOKEN: str = ""
    # CF_MODEL: str = "@cf/meta/llama-3.1-8b-instruct"
    CF_MODEL: str = "@cf/qwen/qwen3.8-27b"


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