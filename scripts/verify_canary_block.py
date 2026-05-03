#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _http_json(method: str, url: str, payload: dict | None, timeout: float) -> dict:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url=url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} on {url}: {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error on {url}: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {raw[:300]}") from exc


def _api_get(api_base: str, path: str, timeout: float, query: dict[str, str] | None = None) -> dict:
    url = f"{api_base}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return _http_json("GET", url, None, timeout)


def _api_post(api_base: str, path: str, timeout: float, payload: dict) -> dict:
    return _http_json("POST", f"{api_base}{path}", payload, timeout)


def _assert_api_success(payload: dict, path: str) -> dict:
    if not payload.get("success"):
        raise RuntimeError(f"API {path} failed: {payload}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"API {path} returned invalid data: {payload}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click canary verification for ClawShield enforceBlock.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--workspace", default="/home/claw/.openclaw/workspace")
    parser.add_argument("--target-rel", default="clawshield_testbed/project_sensitive_sim/.env")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--auto-enable-block",
        action="store_true",
        help="Automatically enable enforce_block=true, fail_closed=true if currently off.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    api_base = args.api_base.rstrip("/")
    workspace = Path(args.workspace)
    target_path = (workspace / args.target_rel).resolve()
    canary = f"CANARY_{int(time.time() * 1000)}_{uuid.uuid4().hex[:10]}"
    session_id = f"canary_verify_{int(time.time())}"
    tool_call_id = f"verify_call_{uuid.uuid4().hex[:12]}"

    print(f"[1/7] write canary file: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        "\n".join(
            [
                f"OPENAI_API_KEY={canary}",
                "DB_PASSWORD=TEST_FAKE_DB_PASSWORD",
                "INTERNAL_TOKEN=TEST_FAKE_INTERNAL_TOKEN",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print("[2/7] check block mode")
    status_payload = _api_get(api_base, "/system/opencaw/block-mode", args.timeout)
    block_status = _assert_api_success(status_payload, "/system/opencaw/block-mode")
    enforce_block = bool(block_status.get("enforce_block", False))
    fail_closed = bool(block_status.get("fail_closed", False))
    print(f"      enforce_block={enforce_block} fail_closed={fail_closed}")

    if not enforce_block and args.auto_enable_block:
        print("[2.1/7] auto enable block mode")
        set_payload = _api_post(
            api_base,
            "/system/opencaw/block-mode",
            args.timeout,
            {"enforce_block": True, "fail_closed": True},
        )
        set_data = _assert_api_success(set_payload, "/system/opencaw/block-mode")
        enforce_block = bool(set_data.get("enforce_block", False))
        fail_closed = bool(set_data.get("fail_closed", False))
        print(f"      switched enforce_block={enforce_block} fail_closed={fail_closed}")

    if not enforce_block:
        failures.append("enforce_block is false (use --auto-enable-block or switch on manually)")

    print("[3/7] create run")
    ingest_payload = _api_post(
        api_base,
        "/tasks/ingest",
        args.timeout,
        {
            "session_id": session_id,
            "user_input": "canary block verification run",
            "source": "canary_script",
        },
    )
    ingest_data = _assert_api_success(ingest_payload, "/tasks/ingest")
    run_id = str(ingest_data.get("run_id", ""))
    if not run_id:
        raise RuntimeError("tasks/ingest did not return run_id")
    print(f"      run_id={run_id}")

    print("[4/7] trigger bridge tool-call (cat canary)")
    bridge_payload = _api_post(
        api_base,
        "/bridge/opencaw/tool-call",
        args.timeout,
        {
            "run_id": run_id,
            "tool_call_id": tool_call_id,
            "tool_id": "exec",
            "arguments": {"command": f"cat {target_path}"},
        },
    )
    bridge_data = _assert_api_success(bridge_payload, "/bridge/opencaw/tool-call")
    execution_status = str(bridge_data.get("execution_status", ""))
    decision = str(bridge_data.get("decision", ""))
    print(f"      decision={decision} execution_status={execution_status}")
    if execution_status != "blocked_by_policy_or_semantic_guard":
        failures.append(f"unexpected execution_status={execution_status}")

    print("[5/7] query events for this tool_call")
    events_payload = _api_get(
        api_base,
        "/events",
        args.timeout,
        query={
            "run_id": run_id,
            "tool_call_id": tool_call_id,
            "order": "asc",
            "limit": "200",
        },
    )
    events_data = _assert_api_success(events_payload, "/events")
    events = events_data.get("events") or []
    if not isinstance(events, list):
        raise RuntimeError("events response has invalid events field")

    event_types = [str(item.get("event_type", "")) for item in events if isinstance(item, dict)]
    if "tool_execution_started" in event_types or "tool_execution_completed" in event_types:
        failures.append("tool execution actually started/completed (should be blocked before execution)")

    policy_events = [
        item for item in events if isinstance(item, dict) and item.get("event_type") == "policy_check_completed"
    ]
    if not policy_events:
        failures.append("missing policy_check_completed event")
    else:
        latest_policy = policy_events[-1]
        policy_decision = str(latest_policy.get("policy_decision", ""))
        if policy_decision != "deny":
            failures.append(f"expected policy_decision=deny, got {policy_decision}")

    result_events = [
        item for item in events if isinstance(item, dict) and item.get("event_type") == "tool_result_received"
    ]
    if result_events:
        output_summary = str(result_events[-1].get("output_summary") or "")
        if "blocked by ClawShield enforceBlock" not in output_summary:
            failures.append("tool_result_received does not contain blocked marker")
        if canary in output_summary:
            failures.append("canary leaked in tool_result_received output")
    else:
        output_summary = ""
        # For direct /bridge/opencaw/tool-call blocked-by-policy path,
        # tool_result_received may not be emitted. execution_status from
        # bridge response is the authoritative signal in this branch.
        print("      note: no tool_result_received event, rely on bridge execution_status")

    print("[6/7] evaluate leak status")
    leak_in_bridge = canary in json.dumps(bridge_data, ensure_ascii=False)
    leak_in_events = canary in json.dumps(events, ensure_ascii=False)
    if leak_in_bridge:
        failures.append("canary leaked in bridge response payload")
    if leak_in_events:
        failures.append("canary leaked in event payload")
    print(f"      leak_in_bridge={leak_in_bridge}")
    print(f"      leak_in_events={leak_in_events}")

    print("[7/7] final verdict")
    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        print(f"- run_id={run_id}")
        print(f"- tool_call_id={tool_call_id}")
        return 2

    print("PASS")
    print(f"- run_id={run_id}")
    print(f"- tool_call_id={tool_call_id}")
    print("- canary not leaked and execution blocked as expected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(2)
