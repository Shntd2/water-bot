from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

from .validator import validate_json_list, validate_json_dict


BASE_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='ignore',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True
    )
    SESSION_SECRET_KEY: str = Field(
        ...,
        description="Session key"
    )
    TELEGRAM_BOT_TOKEN: str = Field(
        ...,
        description="Telegram bot token"
    )
    TELEGRAM_API_BASE_URL: str = Field(
        default="https://api.telegram.org",
        description="Telegram API base URL"
    )

    TELEGRAM_HTTP_TIMEOUT_TOTAL: int = Field(
        default=30,
        description="Total timeout for Telegram HTTP requests in seconds"
    )
    TELEGRAM_HTTP_TIMEOUT_CONNECT: int = Field(
        default=5,
        description="Connection timeout for Telegram HTTP requests in seconds"
    )
    TELEGRAM_HTTP_TIMEOUT_SOCK_READ: int = Field(
        default=10,
        description="Socket read timeout for Telegram HTTP requests in seconds"
    )
    TELEGRAM_HTTP_CONNECTION_LIMIT: int = Field(
        default=100,
        description="Total connection limit for Telegram HTTP client"
    )
    TELEGRAM_HTTP_CONNECTION_LIMIT_PER_HOST: int = Field(
        default=30,
        description="Connection limit per host for Telegram HTTP client"
    )
    TELEGRAM_HTTP_DNS_TTL: int = Field(
        default=300,
        description="DNS cache TTL in seconds for Telegram HTTP client"
    )
    TELEGRAM_HTTP_KEEPALIVE_TIMEOUT: int = Field(
        default=30,
        description="Keepalive timeout for Telegram HTTP connections"
    )

    TELEGRAM_POLLING_INTERVAL: float = Field(
        default=1.0,
        description="Interval in seconds between polling requests to Telegram"
    )
    TELEGRAM_POLLING_TIMEOUT: int = Field(
        default=30,
        description="Long polling timeout in seconds"
    )
    TELEGRAM_POLLING_EXTRA_TIMEOUT: int = Field(
        default=10,
        description="Additional timeout buffer for polling requests"
    )
    TELEGRAM_POLLING_RETRY_DELAY: int = Field(
        default=5,
        description="Delay in seconds before retrying after polling error"
    )
    TELEGRAM_PARSE_MODE: str = Field(
        default="Markdown",
        description="Default parse mode for messages"
    )
    TELEGRAM_DEFAULT_CHAT_ACTION: str = Field(
        default="typing",
        description="Default chat action to send"
    )
    TELEGRAM_WEBHOOK_URL: str = Field(
        ...,
        description="Public URL for Telegram webhook"
    )
    TELEGRAM_WEBHOOK_PATH: str = Field(
        default="/webhook",
        description="Path for webhook endpoint"
    )
    TELEGRAM_WEBHOOK_SECRET: str = Field(
        default="",
        description="Secret token for webhook security"
    )

    BASE_URL: str = Field(
        ...,
        description="Base URL"
    )
    AVAILABLE_LOCATIONS: dict[str, str] = Field(
        ...,
        description="Tracking available districts"
    )

    @field_validator('AVAILABLE_LOCATIONS', mode='before')
    def parse_available_locations(cls, v):
        return validate_json_dict(v, field_name="AVAILABLE_LOCATIONS")

    WHITELIST_LOCATION: list[str] = Field(
        ...,
        description="Whitelist of IP addresses allowed to access health endpoint"
    )

    @field_validator('WHITELIST_LOCATION', mode='before')
    def parse_whitelist_location(cls, v):
        return validate_json_list(v, field_name="WHITELIST_LOCATION")

    REDIS_URL: str = Field(
        ...,
        description="Redis connection URL"
    )
    REDIS_ALERT_TTL: int = Field(
        default=1209600,
        description="TTL for sent alerts in seconds (default: 14 days)"
    )

    POSTGRES_URL: str = Field(
        ...,
        description="PostgreSQL connection URL"
    )
    POSTGRES_ECHO: bool = Field(
        default=False,
        description="SQLAlchemy echo SQL queries"
    )

    HTTP_PROXY: str = Field(
        default="",
        description="HTTP proxy URL (optional, e.g., http://user:pass@proxy:port)"
    )
    HTTPS_PROXY: str = Field(
        default="",
        description="HTTPS proxy URL (optional, e.g., http://user:pass@proxy:port)"
    )


settings = Settings()
