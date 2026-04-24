# ClawShield

ClawShield is a security audit and runtime governance layer for OpenClaw-like tool-calling AI agents.

## Current Stage

This repository is at **Round 10 (demo polish and final delivery)**:

- end-to-end run ingest -> semantic guard -> policy gateway -> telemetry -> report flow
- dashboard with system status, risk overview, and one-click standard scenarios
- report page focused on task/risk/disposition/evidence chain/conclusion
- reproducible demo seeds and fallback free-input prompts
- unified API error contract and baseline regression tests

## Quick Start

1. Install dependencies:

```bash
pip install -e .
```

2. Initialize database:

```bash
python3 scripts/init_db.py
```

3. Start service:

```bash
python3 scripts/dev_start.py
```

4. Open pages:

- Dashboard: `http://127.0.0.1:8000/api/v1/ui/dashboard`
- Swagger: `http://127.0.0.1:8000/docs`

## Full Documentation Manual

For a complete, multi-file project manual (architecture, API, policy, data model, OpenClaw integration, ops, troubleshooting, development constraints), see:

- [`docs/manual/README.md`](docs/manual/README.md)

## Demo Fast Path

1. Seed three standard scenarios:

```bash
python3 scripts/seed_demo_data.py
```

2. Open dashboard and click `run scenario` for:

- `workspace_escape`
- `env_then_http`
- `analysis_high_risk_tool`

3. For each scenario, jump to report page and present:

- final risk/disposition
- highlighted chain path
- key tool calls and resources

## API Highlights

- `GET /api/v1/dashboard/overview`
- `POST /api/v1/dashboard/scenarios/{scenario_id}/run`
- `POST /api/v1/tasks/ingest`
- `POST /api/v1/bridge/opencaw/tool-call`
- `GET /api/v1/runs/{run_id}/report`
- `GET /api/v1/runs/{run_id}/graph`
- `POST /api/v1/bridge/opencaw/session/bootstrap`
- `POST /api/v1/bridge/opencaw/callback/tool-call`
- `POST /api/v1/bridge/opencaw/callback/tool-result`
- `POST /api/v1/bridge/opencaw/callback/message`

## Real OpenClaw Callback Integration

If OpenClaw can call HTTP webhooks, connect it to:

1. Create/resolve run by session:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","user_input":"请分析仓库并总结风险"}'
```

2. Send tool-call events (supports either direct fields or `tool_calls` list):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/tool-call \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","tool_id":"workspace_reader","tool_call_id":"call_1","arguments":{"file_path":"../secret.txt"}}'
```

3. Send tool-result events:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/tool-result \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","tool_result":{"tool_call_id":"call_1","tool_id":"workspace_reader","execution_status":"mock_completed","result_summary":"blocked"}}'
```

4. Send pure chat message events (no tool call required):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/message \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","messages":[{"role":"user","content":"请先审阅代码结构"},{"role":"assistant","content":"好的，我先从目录层级开始。"}]}'
```

5. For generic `exec` tools, pass `arguments.command` to enable automatic intent mapping (`env_read/http/file_read`), so risk chains can be evaluated from callback events.

## Repository Guide

- `app/`: backend code (API/services/policy/analyzer/gateway)
- `configs/`: runtime and rule configuration
- `docs/architecture/`: module and sequence docs for defense
- `docs/manual/`: full maintainer manual (architecture/API/policy/ops/conventions)
- `docs/demo/`: scenarios, runbook, fallback prompts, known limits, presentation points
- `scripts/`: init/start/seed scripts for local demo
- `tests/`: unit + integration tests across round 2-11

## Known Limits (Summary)

- OpenClaw bridge still uses local managed placeholder process in default demo mode
- Tool executors are controlled/mock style for deterministic demos
- Risk chains currently focus on three canonical cases

See full list: [`docs/demo/known_limits.md`](docs/demo/known_limits.md)
