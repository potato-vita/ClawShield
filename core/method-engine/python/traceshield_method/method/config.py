from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


PathLike = Union[str, Path]
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "configs"


def default_config_path(name: str) -> Path:
    return DEFAULT_CONFIG_DIR / name


def resolve_config_path(path: Optional[PathLike], default_name: str) -> Path:
    if path is None:
        return default_config_path(default_name)
    return Path(path)


def load_yaml(path: PathLike) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
