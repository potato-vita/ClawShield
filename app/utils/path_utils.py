from pathlib import Path


def normalize(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
