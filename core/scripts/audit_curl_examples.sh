#!/usr/bin/env bash
set -euo pipefail

base_url="${TRACESHIELD_CORE_BASE_URL:-http://127.0.0.1:8787}"
stamp="$(date +%s%N)"

post_audit() {
  local suffix="$1"
  local tool_name="$2"
  local tool_kind="$3"
  local raw_params="$4"
  local resource_hint="$5"
  local risk_hint="$6"

  curl -fsS -X POST "${base_url}/v1/audit/tool-call" \
    -H 'content-type: application/json' \
    -d "{\"request_id\":\"audit-${stamp}-${suffix}\",\"schema_version\":\"v1\",\"session_id\":\"curl-session-${stamp}\",\"run_id\":\"curl-run-${stamp}\",\"trace_id\":\"curl-trace-${stamp}\",\"tool_call_id\":\"tool-${stamp}-${suffix}\",\"tool_name\":\"${tool_name}\",\"tool_kind\":\"${tool_kind}\",\"raw_params\":${raw_params},\"param_summary\":{},\"resource_hint\":\"${resource_hint}\",\"risk_hint\":\"${risk_hint}\",\"context\":{}}"
  printf '\n'
}

post_audit allow file_read file_read '{"path":"README.md"}' README.md file_read
post_audit secret file_read file_read '{"path":".env"}' .env file_read
post_audit dangerous shell shell_exec '{"cmd":"rm -rf /tmp/traceshield-example"}' 'rm -rf /tmp/traceshield-example' file_delete
post_audit external http_request network_request '{"url":"https://example.com"}' https://example.com network_request
post_audit unknown unknown unknown '{}' unknown unknown
