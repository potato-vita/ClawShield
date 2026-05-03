from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from app.settings import PROJECT_ROOT, get_settings


def normalize_file_resource_id(raw_path: str) -> str:
    text = (raw_path or "").strip()
    if not text:
        return "unknown_file"

    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        text = text[1:-1].strip()
    if not text:
        return "unknown_file"

    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        text = unquote(parsed.path or "")
        if not text:
            return "unknown_file"

    text = text.replace("\\", "/")
    path = Path(text).expanduser()

    try:
        candidate = path if path.is_absolute() else (PROJECT_ROOT / path)
        canonical = candidate.resolve(strict=False)
    except Exception:
        return text

    settings = get_settings()
    workspace_root = Path(settings.workspace_root)
    workspace_abs = workspace_root if workspace_root.is_absolute() else (PROJECT_ROOT / workspace_root)
    workspace_abs = workspace_abs.resolve(strict=False)
    project_abs = PROJECT_ROOT.resolve(strict=False)

    if canonical.is_relative_to(workspace_abs):
        rel = canonical.relative_to(workspace_abs).as_posix()
        return f"./workspace/{rel}" if rel else "./workspace"

    if canonical.is_relative_to(project_abs):
        rel = canonical.relative_to(project_abs).as_posix()
        return f"./{rel}" if rel else "./"

    return canonical.as_posix()
