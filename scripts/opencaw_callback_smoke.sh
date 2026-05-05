#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000/api/v1/bridge/opencaw}"
SESSION_ID="${SESSION_ID:-oc_session_smoke_001}"

echo "[1/4] bootstrap session"
curl -s -X POST "${BASE_URL}/session/bootstrap" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"${SESSION_ID}\",\"user_input\":\"请分析仓库并总结风险\"}"
echo

echo "[2/4] send chat messages"
curl -s -X POST "${BASE_URL}/callback/message" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"${SESSION_ID}\",\"messages\":[{\"role\":\"user\",\"content\":\"请先审阅代码结构\"},{\"role\":\"assistant\",\"content\":\"好的，我先看目录层级。\"}]}"
echo

echo "[3/4] send tool call"
curl -s -X POST "${BASE_URL}/callback/tool-call" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"${SESSION_ID}\",\"tool_id\":\"workspace_reader\",\"tool_call_id\":\"smoke_call_1\",\"arguments\":{\"file_path\":\"./workspace/a.md\"}}"
echo

echo "[4/4] send tool result"
curl -s -X POST "${BASE_URL}/callback/tool-result" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"${SESSION_ID}\",\"tool_result\":{\"tool_call_id\":\"smoke_call_1\",\"tool_id\":\"workspace_reader\",\"execution_status\":\"mock_completed\",\"result_summary\":\"ok\"}}"
echo

echo "smoke_done session_id=${SESSION_ID}"

