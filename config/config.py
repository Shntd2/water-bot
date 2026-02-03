import os
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True
    )
    APP_NAME: str = "Water Bot"
    APP_DESCRIPTION: str = "FastAPI-based Telegram bot that monitors water supply alerts in Yerevan"
    APP_VERSION: str = "1.0"

    HOST: str = os.getenv("HOST")
    PORT: int = int(os.getenv("PORT"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    CACHE_TIMEOUT: int = int(os.getenv("CACHE_TIMEOUT"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT"))
    MAX_REPOSITORIES: int = int(os.getenv("MAX_REPOSITORIES"))

    POOL_CONNECTIONS: int = int(os.getenv("POOL_CONNECTIONS"))
    POOL_MAXSIZE: int = int(os.getenv("POOL_MAXSIZE"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES"))
    POOL_BLOCK: bool = os.getenv("POOL_BLOCK", "False").lower() in ("true", "1", "yes")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
