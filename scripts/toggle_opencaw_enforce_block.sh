#!/usr/bin/env bash
set -euo pipefail

KEY_ENFORCE="plugins.entries.clawshield-tool-bridge.config.enforceBlock"
KEY_FAIL_CLOSED="plugins.entries.clawshield-tool-bridge.config.failClosed"
OPENCLAW_CONFIG_PATH="${HOME}/.openclaw/openclaw.json"

mode="${1:-status}"
fail_closed="${2:-false}"

usage() {
  cat <<'EOF'
Usage:
  scripts/toggle_opencaw_enforce_block.sh status
  scripts/toggle_opencaw_enforce_block.sh on [failClosed=true|false]
  scripts/toggle_opencaw_enforce_block.sh off

Examples:
  scripts/toggle_opencaw_enforce_block.sh on true
  scripts/toggle_opencaw_enforce_block.sh off
  scripts/toggle_opencaw_enforce_block.sh status
EOF
}

read_mode_from_config() {
  if [[ ! -f "${OPENCLAW_CONFIG_PATH}" ]]; then
    echo "openclaw config file not found: ${OPENCLAW_CONFIG_PATH}" >&2
    return 1
  fi

  python3 - "${OPENCLAW_CONFIG_PATH}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
config = (
    data.get("plugins", {})
    .get("entries", {})
    .get("clawshield-tool-bridge", {})
    .get("config", {})
)
enforce = bool(config.get("enforceBlock", False))
fail_closed = bool(config.get("failClosed", False))
print(f"enforceBlock={str(enforce).lower()}")
print(f"failClosed={str(fail_closed).lower()}")
PY
}

run_openclaw() {
  local output
  if ! output="$(openclaw "$@" 2>&1)"; then
    echo "${output}" >&2
    return 1
  fi
}

case "${mode}" in
  on)
    run_openclaw config set "${KEY_ENFORCE}" true --strict-json
    run_openclaw config set "${KEY_FAIL_CLOSED}" "${fail_closed}" --strict-json
    run_openclaw gateway restart
    ;;
  off)
    run_openclaw config set "${KEY_ENFORCE}" false --strict-json
    run_openclaw config set "${KEY_FAIL_CLOSED}" false --strict-json
    run_openclaw gateway restart
    ;;
  status)
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown mode: ${mode}" >&2
    usage
    exit 1
    ;;
esac

read_mode_from_config
