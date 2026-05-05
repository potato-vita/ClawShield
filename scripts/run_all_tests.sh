#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source .venv/bin/activate
python3 -m unittest $(find tests -type f -name 'test_*.py' | sed 's#/#.#g; s#\.py$##' | tr '\n' ' ')
