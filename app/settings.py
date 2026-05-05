from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "ClawShield"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8000
    config_path: str = "configs/app.yaml"
    database_url: str = "sqlite:///./data/clawshield.db"
    log_level: str = "INFO"
    openclaw_auto_launch: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLAWSHIELD_",
        extra="ignore",
    )


def _load_yaml_config(config_path: str) -> dict[str, Any]:
    path = _resolve_project_path(config_path)
    if not path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise RuntimeError(f"Config file must contain a mapping: {config_path}")

    return loaded


def _resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _normalize_database_url(database_url: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url

    db_path = database_url[len(sqlite_prefix) :]
    if db_path == ":memory:" or db_path.startswith("/"):
        return database_url

    resolved = (PROJECT_ROOT / db_path).resolve()
    return f"{sqlite_prefix}{resolved}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_settings = Settings()
    resolved_config_path = str(_resolve_project_path(env_settings.config_path))
    yaml_values = _load_yaml_config(resolved_config_path)

    merged = env_settings.model_dump()
    merged.update(yaml_values)

    # Environment variables still win if explicitly set.
    merged.update(Settings().model_dump(exclude_unset=True))
    merged["config_path"] = resolved_config_path
    merged["database_url"] = _normalize_database_url(str(merged.get("database_url", env_settings.database_url)))

    return Settings(**merged)
