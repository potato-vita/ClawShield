from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundSixTimelineTestCase(unittest.TestCase):
    def test_event_query_and_timeline_with_run_status_progression(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round6",
                    "user_input": "请分析工作区文件",
                    "source": "ui",
                    "metadata": {"round": 6},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            tool_call_resp = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round6_file",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/demo.txt"},
                },
            )
            self.assertEqual(tool_call_resp.status_code, 200)

            tool_result_resp = client.post(
                "/api/v1/bridge/opencaw/tool-result",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round6_file",
                    "tool_id": "workspace_reader",
                    "result_summary": "mock read completed",
                    "raw_result": {"ok": True},
                    "execution_status": "ok",
                    "latency_ms": 5,
                },
            )
            self.assertEqual(tool_result_resp.status_code, 200)

            events_resp = client.get(
                "/api/v1/events",
                params={"run_id": run_id, "order": "asc", "limit": 200, "offset": 0},
            )
            self.assertEqual(events_resp.status_code, 200)
            events = events_resp.json()["data"]["events"]
            self.assertGreater(len(events), 0)

            # Ensure normalized fields are present in event payloads.
            sample = events[0]
            for field in [
                "session_id",
                "event_stage",
                "actor_type",
                "tool_id",
                "resource_type",
                "resource_id",
                "semantic_decision",
                "policy_decision",
                "risk_level",
                "disposition",
                "status",
            ]:
                self.assertIn(field, sample)

            # Filter by event type should return matching subset.
            filtered_resp = client.get(
                "/api/v1/events",
                params={"run_id": run_id, "event_type": "tool_call_requested"},
            )
            self.assertEqual(filtered_resp.status_code, 200)
            filtered = filtered_resp.json()["data"]["events"]
            self.assertTrue(all(item["event_type"] == "tool_call_requested" for item in filtered))

            timeline_resp = client.get(f"/api/v1/runs/{run_id}/timeline")
            self.assertEqual(timeline_resp.status_code, 200)
            timeline = timeline_resp.json()["data"]["timeline"]
            self.assertGreater(len(timeline), 0)

            timestamps = [datetime.fromisoformat(item["ts"].replace("Z", "+00:00")) for item in timeline]
            self.assertEqual(timestamps, sorted(timestamps))

            run_resp = client.get(f"/api/v1/runs/{run_id}")
            self.assertEqual(run_resp.status_code, 200)
            self.assertEqual(run_resp.json()["data"]["status"], "finished")


if __name__ == "__main__":
    unittest.main()
