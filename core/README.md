# TraceShield Core

TraceShield Core is the FastAPI and SQLite service that replaces `mock-core` and provides database-backed APIs for the TraceShield frontend.

## Requirements

- Python 3.11 or newer

## Local Setup

```bash
cd core
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run Tests

```bash
cd core
source .venv/bin/activate
pytest -q
```

## Start The Service

```bash
cd core
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then verify:

```bash
curl http://127.0.0.1:8000/api/module4/health
```

Expected response:

```json
{
  "success": true,
  "database": "not_initialized",
  "service": "traceshield-core",
  "version": "0.1.0"
}
```

## Main APIs

- `POST /v1/audit/tool-call`
- `POST /v1/events/batch`
- `GET /api/module4/dashboard`
- `GET /api/module4/events/{event_id}`
- `POST /api/module4/reports`
- `GET /api/module4/exports/{filename}`
- `/sessions` session, chat, approval, abort and upload endpoints
- `/api/module4/policies` policy management endpoints

The three-column frontend is served at `http://127.0.0.1:8000/`.

## End-to-End Demo

```bash
cd core
bash scripts/e2e_demo.sh
```

See `docs/e2e_demo.md` and `docs/test_report.md` for the reproducible flow and expected results.
