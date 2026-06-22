#!/usr/bin/env bash
set -euo pipefail
CORE_URL="${CORE_URL:-http://127.0.0.1:8000}"
CURL=(curl --noproxy 127.0.0.1 -fsS)

"${CURL[@]}" "$CORE_URL/api/module4/health"
echo
"${CURL[@]}" "$CORE_URL/api/module4/dashboard?time_range=7d"
echo
SESSION_JSON=$("${CURL[@]}" -X POST "$CORE_URL/sessions" -H 'content-type: application/json' -d '{"title":"Smoke session"}')
SESSION_ID=$(printf '%s' "$SESSION_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
"${CURL[@]}" -X POST "$CORE_URL/sessions/$SESSION_ID/chat" -H 'content-type: application/json' -d '{"message":"最近 7 天有哪些高风险事件？"}'
echo
