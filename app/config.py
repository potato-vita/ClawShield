from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLAWSHIELD_", env_file=".env", extra="ignore")

    app_name: str = "ClawShield Demo"
    debug: bool = False
    database_url: str = "sqlite:///./app/data/clawshield.db"
    rules_path: str = "rules/boundary_rules.yaml"
    risk_rules_path: str = "rules/risk_rules.yaml"
    workspace_root: str = "app/data/sample_workspace"
    report_export_dir: str = "app/data/reports"
    log_file: str = "app/data/clawshield.log"
    default_actor: str = "openclaw"
    version: str = "0.1.0"
    preaudit_keywords: list[str] = Field(
        default_factory=lambda: ["subprocess", "os.system", "eval(", "exec(", "requests.post"]
    )

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (PROJECT_ROOT / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
