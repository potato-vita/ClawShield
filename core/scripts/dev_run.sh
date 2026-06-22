#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port "${TRACESHIELD_CORE_PORT:-8000}"
