#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CORE_URL="${CORE_URL:-http://127.0.0.1:8000}"
CURL=(curl --noproxy 127.0.0.1 -fsS)
LOG_FILE=/tmp/traceshield-core-e2e.log

bash scripts/reset_db.sh
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$LOG_FILE" 2>&1 &
CORE_PID=$!
trap 'kill "$CORE_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if "${CURL[@]}" "$CORE_URL/api/module4/health" >/dev/null 2>&1; then break; fi
  sleep 0.2
done

audit() {
  local id="$1" kind="$2" params="$3"
  "${CURL[@]}" -X POST "$CORE_URL/v1/audit/tool-call" -H 'content-type: application/json' \
    -d "{\"schema_version\":\"v1\",\"session_id\":\"sess_e2e\",\"run_id\":\"run_e2e\",\"trace_id\":\"trace_e2e\",\"tool_call_id\":\"$id\",\"tool_name\":\"exec\",\"tool_kind\":\"$kind\",\"raw_params\":$params,\"context\":{\"user_goal\":\"E2E 安全验证\",\"username\":\"e2e-user\",\"department_name\":\"研发部\"}}"
}

echo "[1/9] ALLOW"; audit call_e2e_allow file_read '{"path":"README.md"}' | tee /tmp/e2e-allow.json; echo
echo "[2/9] BLOCK"; audit call_e2e_block shell_exec '{"cmd":"cat .env"}' | tee /tmp/e2e-block.json; echo
echo "[3/9] ASK"; audit call_e2e_ask network_request '{"url":"https://external-upload.com/drop"}' | tee /tmp/e2e-ask.json; echo

echo "[4/9] Event batch"
"${CURL[@]}" -X POST "$CORE_URL/v1/events/batch" -H 'content-type: application/json' -d '{"events":[{"event_id":"evt_e2e_before","schema_version":"v1","type":"before_tool_call","session_id":"sess_e2e","run_id":"run_e2e","trace_id":"trace_e2e","timestamp":1782100000000,"payload":{"tool_call_id":"call_e2e_event","tool_name":"read","tool_kind":"file_read","params":{"path":"README.md"}}},{"event_id":"evt_e2e_after","schema_version":"v1","type":"after_tool_call","session_id":"sess_e2e","run_id":"run_e2e","trace_id":"trace_e2e","timestamp":1782100001000,"payload":{"tool_call_id":"call_e2e_event","tool_name":"read","tool_kind":"file_read","result_preview":"TraceShield","result_size":11}}]}'
echo

echo "[5/9] Dashboard"
"${CURL[@]}" "$CORE_URL/api/module4/dashboard?time_range=7d" | tee /tmp/e2e-dashboard.json; echo
EVENT_ID=$(.venv/bin/python -c 'import json; d=json.load(open("/tmp/e2e-dashboard.json")); print(d["data"]["high_risk_events"][0]["event_id"])')

echo "[6/9] Event detail: $EVENT_ID"
"${CURL[@]}" "$CORE_URL/api/module4/events/$EVENT_ID"; echo

echo "[7/9] Session and chat"
"${CURL[@]}" -X POST "$CORE_URL/sessions" -H 'content-type: application/json' -d '{"title":"E2E 分析"}' | tee /tmp/e2e-session.json; echo
SESSION_ID=$(.venv/bin/python -c 'import json; print(json.load(open("/tmp/e2e-session.json"))["id"])')
"${CURL[@]}" -X POST "$CORE_URL/sessions/$SESSION_ID/chat" -H 'content-type: application/json' -d '{"message":"最近 7 天有哪些高风险事件？"}'; echo

echo "[8/9] Report"
"${CURL[@]}" -X POST "$CORE_URL/api/module4/reports" -H 'content-type: application/json' -d "{\"session_id\":\"$SESSION_ID\",\"title\":\"E2E 安全报告\",\"time_range\":\"7d\"}" | tee /tmp/e2e-report.json; echo
DOWNLOAD_URL=$(.venv/bin/python -c 'import json; print(json.load(open("/tmp/e2e-report.json"))["download_url"])')
"${CURL[@]}" "$CORE_URL$DOWNLOAD_URL" >/tmp/e2e-report.html
test -s /tmp/e2e-report.html

echo "[9/9] Complete: dashboard event=$EVENT_ID session=$SESSION_ID report=$DOWNLOAD_URL"
