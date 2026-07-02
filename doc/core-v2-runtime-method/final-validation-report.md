# TraceShield Core v2 Final Validation Report

## Scope

- Branch: `feature/runtime-method-engine`
- Base: `frontend@c18ffc4590bacf957428d5bab3e032474945e89d`
- Date: 2026-07-02
- Plan: `TraceShield_Core_v2_Codex_多轮替换执行方案.md`
- Result: Phases 0-9 completed; local Core runs in controlled `enforce` mode with legacy fallback.

## Delivered Areas

1. Stable OpenClaw correlation: one `tool_call_id` and run-level `step_seq` shared by synchronous audit, before event, and after event.
2. Independent Python JSONL Runtime Method Engine with versioned protocol, stderr-only logs, timeout, restart, backpressure, and health reporting.
3. Shadow storage and diagnostics using isolated method evaluation, violation, and graph tables.
4. Transient full-observation injection detection; only hash, redacted preview, and detection metadata persist.
5. Replay admission gate and balanced-v1 current-step decision mapping.
6. Enforce orchestration with safety floor, legacy failure fallback, and environment-only rollback.
7. Method-first risk graph with compatible legacy fallback and Web adapter support.

The detailed per-phase changes, failures, and fixes are recorded in `runtime-method-engine-progress.md`.

## Database Migrations

- `002_runtime_ordering.sql`: stable step ordering, correlation metadata, run lifecycle.
- `003_method_shadow.sql`: method evaluations, violations, graph snapshots, semantic and observation metadata.
- `004_enforce_metadata.sql`: decision engine provenance and method evaluation reference.

Migration discovery is ordered and repeatable. Final database check found 14/14 expected tables and 4 policies.

## Final Commands and Results

```bash
cd openclaw-plugin
npm run typecheck
npm test -- --run
npm run build
# 9 files, 35/35 tests passed

cd core
npm run typecheck
npm test -- --run
npm run build
npm run db:check
npm run smoke
# 5 files, 13/13 tests; 14/14 tables; smoke 14/14

cd core/method-engine
.venv/bin/python -m pytest -q
# 38/38 tests passed

cd core
npm run method:replay
# 12/12 fixtures; 240/240 requests; 100% availability; 0 timeout/error

cd web
npm run typecheck
npm run build
npm run smoke
# passed

git diff --check
# passed
```

Latest replay latency: p50 38.03ms, p95 68.18ms, p99 98.99ms. Every BLOCK has current-step evidence, history-only risk remains WARN, and unknown tools remain ASK.

## Real OpenClaw Validation

The non-interactive `openclaw agent --json` command was used because `openclaw chat` is an interactive TUI.

| Session | Tool | Result | Persisted decision |
| --- | --- | --- | --- |
| `corev2-safe-read` | `read` public README | completed | method WARN |
| `corev2-block-read` | `read` `.env` | blocked; file not read | method BLOCK |
| `corev2-status-v2` | `traceshield_status` | completed; failures 0 | method ALLOW |

The status call reported the plugin loaded, Core at `http://127.0.0.1:8787`, fallback enabled, and the event queue operating.

## Correlation and Privacy Evidence

Database queries for the three real runs show:

- exactly one `tool_calls` row and one `tool_results` row per run/step;
- `correlation_source=openclaw_id` and stable `step_seq=1`;
- before/after processing converges on the same tool call row;
- `tool_results.raw_result IS NULL`;
- `trace_events.raw_payload IS NULL`;
- sensitive-read content was not stored as a raw result.

## Runtime Health

```text
Core: ok=true, db_connected=true
Method: mode=enforce, available=true, queue_depth=0, pending_requests=0
Web: HTTP 200
OpenClaw Gateway: event loop healthy
```

Worker termination was also tested: the current audit fell back to legacy, then the worker restarted and method availability recovered. A separate process with `TRACESHIELD_ENGINE_MODE=legacy` verified rollback without starting Python.

## Final Defect Resolution

The first status-tool test exposed a missing semantic registry entry: `traceshield_status` was unknown, producing ASK with no approval route. Registry v2 adds an exact low-risk `status_read` mapping, the default intent frame allows it, replay now includes that fixture, and the second real call succeeded.

## Residual Risks

- The imported experiment source has no supplied license file; redistribution still requires source-owner confirmation.
- Run context is process-local; multi-process Gateway deployment would require shared correlation state or upstream stable identifiers.
- The 120ms method timeout is currently suitable for local measured latency but should be monitored on slower hosts.
- Historical Shadow data intentionally retains one Phase 5 cold-start timeout.
- The local PostgreSQL restart/bind/credential hardening items from the earlier reliability review remain separate deployment work.
