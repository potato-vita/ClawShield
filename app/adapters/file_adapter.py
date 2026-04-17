from pathlib import Path

from app.core.workspace_guard import WorkspaceGuard
from app.utils.path_utils import ensure_parent


class FileAdapter:
    def __init__(self, workspace_guard: WorkspaceGuard):
        self.guard = workspace_guard

    def read(self, path: str) -> str:
        safe = self.guard.guard_read(path)
        if not safe.exists():
            return ""
        return safe.read_text(encoding="utf-8", errors="ignore")

    def write(self, path: str, content: str) -> bool:
        safe = self.guard.guard_write(path)
        ensure_parent(Path(safe))
        safe.write_text(content, encoding="utf-8")
        return True
