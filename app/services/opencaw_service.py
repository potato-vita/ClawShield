from __future__ import annotations

import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import yaml


class OpenClawService:
    """Manage OpenClaw process lifecycle with explicit, thread-safe state."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "configs" / "opencaw_bridge.yaml"
        self._config_path = Path(config_path) if config_path else default_path
        self._lock = RLock()
        self._process: subprocess.Popen[bytes] | None = None
        self._mode: str | None = None
        self._started_at: datetime | None = None
        self._last_error: str | None = None

    def _load_config(self) -> dict[str, Any]:
        if not self._config_path.exists():
            raise RuntimeError(f"OpenClaw bridge config not found: {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        if not isinstance(loaded, dict):
            raise RuntimeError("OpenClaw bridge config must be a mapping.")
        return loaded

    def _is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _cleanup_finished_process(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            return

        self._process = None
        self._mode = None
        self._started_at = None

    def _resolve_launch_command(self, config: dict[str, Any]) -> list[str]:
        configured = str(config.get("launch_command", "")).strip()
        if configured:
            return shlex.split(configured)

        mode = str(config.get("mode", "placeholder")).strip().lower()
        if mode != "placeholder":
            raise RuntimeError("launch_command is required when bridge mode is not placeholder.")

        # Placeholder mode simulates a long-lived process in local development.
        return [sys.executable, "-c", "import time; time.sleep(3600)"]

    def _stop_timeout_seconds(self) -> int:
        config = self._load_config()
        timeout_raw = config.get("timeout_seconds", 10)
        try:
            return max(int(timeout_raw), 1)
        except (TypeError, ValueError):
            return 10

    def status(self) -> dict:
        with self._lock:
            self._cleanup_finished_process()
            running = self._is_running()

            return {
                "managed": running,
                "state": "running" if running else "stopped",
                "pid": self._process.pid if running and self._process else None,
                "mode": self._mode,
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "last_error": self._last_error,
            }

    def start(self, mode: str = "dev") -> dict:
        with self._lock:
            self._cleanup_finished_process()
            if self._is_running():
                payload = self.status()
                payload["already_running"] = True
                return payload

            config = self._load_config()
            if not bool(config.get("enabled", True)):
                raise RuntimeError("OpenClaw bridge is disabled by configuration.")

            command = self._resolve_launch_command(config)

            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as exc:
                self._last_error = f"{exc.__class__.__name__}: {exc}"
                raise RuntimeError("Failed to start OpenClaw managed process.") from exc

            self._process = process
            self._mode = mode
            self._started_at = datetime.now(timezone.utc)
            self._last_error = None
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            self._cleanup_finished_process()
            process = self._process

            if process is None or process.poll() is not None:
                self._process = None
                self._mode = None
                self._started_at = None
                return {
                    "managed": False,
                    "state": "stopped",
                    "pid": None,
                    "stopped_at": datetime.now(timezone.utc).isoformat(),
                    "already_stopped": True,
                }

            timeout_seconds = self._stop_timeout_seconds()
            process.terminate()
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

            self._process = None
            self._mode = None
            self._started_at = None
            return {
                "managed": False,
                "state": "stopped",
                "pid": None,
                "stopped_at": datetime.now(timezone.utc).isoformat(),
                "last_error": self._last_error,
            }

    def shutdown(self) -> None:
        self.stop()


opencaw_service = OpenClawService()
