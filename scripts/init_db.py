from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def main() -> None:
    _ensure_project_root_on_path()

    from app.db import init_database

    init_database()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
