from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.opencaw_block_mode_service import OpenClawBlockModeService


class OpenClawBlockModeServiceTestCase(unittest.TestCase):
    def test_status_reads_mode_from_openclaw_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "openclaw.json"
            script_path = Path(tmpdir) / "toggle.sh"
            script_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script_path.chmod(0o755)

            config_path.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "entries": {
                                "clawshield-tool-bridge": {
                                    "config": {"enforceBlock": True, "failClosed": True}
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            service = OpenClawBlockModeService(script_path=script_path, config_path=config_path)
            status = service.status()
            self.assertTrue(status["enforce_block"])
            self.assertTrue(status["fail_closed"])
            self.assertEqual(status["config_path"], str(config_path))

    def test_set_mode_invokes_toggle_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "openclaw.json"
            script_path = Path(tmpdir) / "toggle.sh"
            script_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            script_path.chmod(0o755)

            config_path.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "entries": {
                                "clawshield-tool-bridge": {
                                    "config": {"enforceBlock": False, "failClosed": False}
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            service = OpenClawBlockModeService(script_path=script_path, config_path=config_path)

            def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
                del kwargs
                command = args[0]
                config_path.write_text(
                    json.dumps(
                        {
                            "plugins": {
                                "entries": {
                                    "clawshield-tool-bridge": {
                                        "config": {"enforceBlock": True, "failClosed": True}
                                    }
                                }
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(command, [str(script_path), "on", "true"])
                class Result:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return Result()

            with patch("app.services.opencaw_block_mode_service.subprocess.run", side_effect=fake_run):
                updated = service.set_mode(enforce_block=True, fail_closed=True)
            self.assertTrue(updated["enforce_block"])
            self.assertTrue(updated["fail_closed"])


if __name__ == "__main__":
    unittest.main()

