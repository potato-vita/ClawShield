from pathlib import Path
from fnmatch import fnmatch

from app.core.exceptions import WorkspaceViolationError


class WorkspaceGuard:
    def __init__(self, workspace_root: str, sensitive_patterns: list[str] | None = None):
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.sensitive_patterns = sensitive_patterns or []

    def normalize_path(self, path: str) -> Path:
        raw = Path(path)
        if raw.is_absolute():
            resolved = raw.expanduser().resolve()
        else:
            resolved = (self.workspace_root / raw).resolve()
        return resolved

    def is_within_workspace(self, path: str) -> bool:
        resolved = self.normalize_path(path)
        try:
            resolved.relative_to(self.workspace_root)
            return True
        except ValueError:
            return False

    def is_sensitive_path(self, path: str) -> bool:
        resolved = self.normalize_path(path)
        rel = resolved
        try:
            rel = resolved.relative_to(self.workspace_root)
        except ValueError:
            pass

        rel_text = str(rel)
        name = resolved.name
        for pattern in self.sensitive_patterns:
            if fnmatch(rel_text, pattern) or fnmatch(name, pattern):
                return True
        return False

    def guard_read(self, path: str) -> Path:
        resolved = self.normalize_path(path)
        if not self.is_within_workspace(path):
            raise WorkspaceViolationError(f"Read denied outside workspace: {resolved}")
        return resolved

    def guard_write(self, path: str) -> Path:
        resolved = self.normalize_path(path)
        if not self.is_within_workspace(path):
            raise WorkspaceViolationError(f"Write denied outside workspace: {resolved}")
        return resolved
