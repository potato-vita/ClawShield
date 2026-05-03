from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


class OpenClawBlockModeService:
    """Manage OpenClaw bridge block-mode via local toggle script."""

    def __init__(
        self,
        script_path: str | Path | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self._script_path = Path(script_path) if script_path else repo_root / "scripts" / "toggle_opencaw_enforce_block.sh"
        self._config_path = Path(config_path) if config_path else Path.home() / ".openclaw" / "openclaw.json"
        self._lock = RLock()

    def status(self) -> dict[str, Any]:
        with self._lock:
            mode = self._read_mode()
            return {
                "enforce_block": mode["enforce_block"],
                "fail_closed": mode["fail_closed"],
                "config_path": str(self._config_path),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    def set_mode(self, enforce_block: bool, fail_closed: bool = True) -> dict[str, Any]:
        with self._lock:
            if not self._script_path.exists():
                raise RuntimeError(f"toggle script not found: {self._script_path}")

            command: list[str]
            if enforce_block:
                command = [str(self._script_path), "on", "true" if fail_closed else "false"]
            else:
                command = [str(self._script_path), "off"]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise RuntimeError(f"failed to switch OpenClaw block mode: {detail}")

            mode = self._read_mode()
            return {
                "enforce_block": mode["enforce_block"],
                "fail_closed": mode["fail_closed"],
                "config_path": str(self._config_path),
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }

    def _read_mode(self) -> dict[str, bool]:
        if not self._config_path.exists():
            raise RuntimeError(f"openclaw config not found: {self._config_path}")

        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"invalid openclaw config: {exc}") from exc

        config = (
            payload.get("plugins", {})
            .get("entries", {})
            .get("clawshield-tool-bridge", {})
            .get("config", {})
        )
        return {
            "enforce_block": bool(config.get("enforceBlock", False)),
            "fail_closed": bool(config.get("failClosed", False)),
        }


opencaw_block_mode_service = OpenClawBlockModeService()

