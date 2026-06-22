#!/usr/bin/env bash
set -euo pipefail
CORE_URL="${CORE_URL:-http://127.0.0.1:8000}"

post_audit() {
  local call_id="$1" kind="$2" params="$3"
  curl --noproxy 127.0.0.1 -fsS -X POST "$CORE_URL/v1/audit/tool-call" \
    -H 'content-type: application/json' \
    -d "{\"schema_version\":\"v1\",\"session_id\":\"sess_smoke\",\"run_id\":\"run_smoke\",\"trace_id\":\"trace_smoke\",\"tool_call_id\":\"$call_id\",\"tool_name\":\"exec\",\"tool_kind\":\"$kind\",\"raw_params\":$params,\"context\":{\"user_goal\":\"smoke\"}}"
}

ALLOW=$(post_audit call_smoke_allow file_read '{"path":"README.md"}')
BLOCK=$(post_audit call_smoke_block shell_exec '{"cmd":"cat .env"}')
ASK=$(post_audit call_smoke_ask network_request '{"url":"https://external-upload.com/drop"}')
echo "ALLOW: $ALLOW"
echo "BLOCK: $BLOCK"
echo "ASK: $ASK"
