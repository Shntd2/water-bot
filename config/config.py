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

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    CACHE_TIMEOUT: int = 3600
    MAX_WORKERS: int = 4
    REQUEST_TIMEOUT: int = 15
    MAX_REPOSITORIES: int = 50

    POOL_CONNECTIONS: int = 10
    POOL_MAXSIZE: int = 20
    MAX_RETRIES: int = 3
    POOL_BLOCK: bool = False

    LOG_LEVEL: str = "INFO"


settings = Settings()
