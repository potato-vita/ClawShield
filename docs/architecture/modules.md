# Module Responsibilities (Round 10)

## HTTP Layer (`app/api`)

- Owns request/response contracts only.
- Delegates orchestration to service layer.
- Uses unified `AppError` contract for all failures.

## Service Layer (`app/services`)

- `task_service`: run/task ingest transaction.
- `bridge_service`: semantic decision + policy gateway execution orchestration.
- `report_service`: timeline + graph + risk finding aggregation.
- `demo_service`: one-click standard scenario orchestration for live demo.
- `audit_service`: normalized event recording/query.

## Policy Layer (`app/policy`)

- Loads YAML rule bundles from `configs/rules`.
- Matches task/tool/resource rules and emits explain lines.
- Produces disposition/risk output for gateway.

## Gateway Layer (`app/gateway`)

- Interceptors normalize resources from action requests.
- Executors run controlled side effects (demo-safe behavior).
- `gateway_manager` is the single orchestration entry for runtime actions.

## Analyzer Layer (`app/analyzer`)

- Builds timeline, evidence graph, and risk-chain findings.
- Produces run-level conclusion used by report and dashboard.

## Demo Catalog (`app/demo`)

- Single source of truth for:
  - three standard scenarios
  - safe/risk fallback free-input prompts

## Persistence Layer (`app/models`, `app/repositories`)

- SQLAlchemy entities for runs/tasks/events/findings/reports.
- Repositories keep SQL access out of business orchestration.
