from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.demo.scenarios import list_standard_scenarios
from app.main import app


def seed_demo_data() -> list[str]:
    run_ids: list[str] = []
    with TestClient(app) as client:
        for scenario in list_standard_scenarios():
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": scenario.session_id,
                    "user_input": scenario.prompt,
                    "source": "seed",
                    "metadata": {
                        "seed": True,
                        "scenario_id": scenario.scenario_id,
                    },
                },
            )
            ingest_resp.raise_for_status()
            run_id = ingest_resp.json()["data"]["run_id"]

            for index, call in enumerate(scenario.calls, start=1):
                payload = {
                    "run_id": run_id,
                    "tool_call_id": f"{call.tool_call_id}_{index}",
                    "tool_id": call.tool_id,
                    "arguments": call.arguments,
                }
                tool_resp = client.post("/api/v1/bridge/opencaw/tool-call", json=payload)
                tool_resp.raise_for_status()

            # Force report generation so graph/risk summaries are materialized.
            report_resp = client.get(f"/api/v1/runs/{run_id}/report")
            report_resp.raise_for_status()
            run_ids.append(run_id)

    return run_ids


if __name__ == "__main__":
    seeded = seed_demo_data()
    print("seeded_run_ids=")
    for run_id in seeded:
        print(f"- {run_id}")
