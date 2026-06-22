#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
rm -f app/data/traceshield.db
.venv/bin/python -m app.db.init_db_cli
