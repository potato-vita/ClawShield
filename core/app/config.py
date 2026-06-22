from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "traceshield-core"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = Field(
        default="sqlite:///./app/data/traceshield.db",
        validation_alias="TRACESHIELD_DATABASE_URL",
    )
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TRACESHIELD_CORE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
