# TraceShield Core v2 Runtime Method Engine Progress

## Execution Context

- Branch: `feature/runtime-method-engine`
- Base: `frontend@c18ffc4590bacf957428d5bab3e032474945e89d`
- Started: 2026-07-02
- Plan: `TraceShield_Core_v2_Codex_多轮替换执行方案.md`

## Phase Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0 | completed | Method core imported; 29 isolated tests pass. |
| Phase 1 | completed | Stable IDs, run-level step sequence, RunLifecycle. |
| Phase 2 | completed | Versioned Python JSONL worker and balanced-v1 mapper. |
| Phase 3 | completed | TypeScript lifecycle, correlation, timeout, restart, backpressure. |
| Phase 4 | completed | Shadow schema, intent frame, trace assembly, repositories. |
| Phase 5 | completed | Non-blocking shadow integration and diagnostics. |
| Phase 6 | completed | Transient full-observation detection and revisioned re-evaluation. |
| Phase 7 | completed | 12 scenarios, 240 requests, admission metrics pass. |
| Phase 8 | completed | Method-primary enforce, safety floor, legacy fallback/rollback. |
| Phase 9 | completed | Method-first graph with legacy fallback; docs/deployment updated. |

## Phase 1 - Stable IDs, step_seq, RunLifecycle

### Changes

- Added process-wide `RunContextRegistry` with pending-call correlation and run cleanup.
- Synchronous AuditRequest and asynchronous before/after events now reuse one tool call ID and step sequence.
- Added optional v1-compatible ordering fields to plugin/Core contracts.
- Added repeatable `002_runtime_ordering.sql` and migration discovery.
- Added run completion on `agent_end`.
- Exposed ordering and lifecycle fields in query APIs.

### Validation

- Plugin: typecheck/build passed; 35/35 tests passed.
- Hook correlation test compares AuditRequest, before event, and after event IDs/steps.
- Core: typecheck/build passed; migration succeeded twice; db check passed; smoke 14/14 passed.
- Method core: 29/29 passed.
- Web: typecheck/build/smoke passed.

### Failure and Fix

- Existing database migration initially failed because `schema.sql` attempted to create a step index before the migration added the column. New indexes are now owned by migration 002, allowing old and fresh databases to initialize safely.

## Phase 2 - Python JSONL Worker

- Added versioned runtime schemas, adapter, decision mapper, graph projection, and worker.
- Worker supports health, evaluate, shutdown, structured errors, and stderr-only logs.
- Added balanced-v1 behavior outside the imported method package.
- Python suite: 37/37 passed, including 100-request longevity and history/current-step separation.
- Plugin/Core/Web regression passed.

## Phase 3 - TypeScript Worker Client

- Added process lifecycle, JSONL parsing, pending correlation, timeout, queue limit, restart, and health helpers.
- Added Vitest to Core and method health scripts.
- Core engine tests: 5/5 passed, including real worker 100 concurrent health requests and kill/restart.
- First typecheck found variable shadowing and an exact optional property mismatch; both were fixed without changing behavior.
- Plugin 35/35, Python 37/37, Core smoke 14/14, and Web regression passed.

## Phase 4 - Shadow Storage and Trace Assembly

- Added migration 003 and three isolated method tables; migrations pass twice and db check reports 14/14 tables.
- Added versioned IntentFrameBuilder, step-ordered TraceAssembler, semantic hints, repository, and diff classifier.
- Core tests increased to 10/10; plugin/Python/Core/Web regressions passed.

## Phase 5 - Shadow Integration

- Legacy transaction commits before a fire-and-forget bounded Shadow enqueue.
- Added worker lifecycle on Core startup/shutdown, failure persistence, SSE, and diagnostic APIs.
- Live smoke kept all 14 legacy decisions unchanged and produced queryable method results/graphs/diffs.
- One first background request timed out at the 120ms client budget while the legacy response succeeded; later method compute latency was 0.4-3.8ms. This remains visible for Phase 7 admission statistics.

## Phase 6 - Observation Detection

- Added a loopback-only transient observation request that bypasses memory/disk event queues.
- Full observation is scanned in Python memory; only detection result, hash, and redacted preview persist.
- Fixed result summary to redact before truncation.
- Late observation triggers revisioned re-evaluation of subsequent steps.
- Live verification detected an injection beyond 600 characters, created revision 2, and confirmed `raw_result IS NULL` and zero persisted raw payloads.
- Python 38/38, plugin 35/35, Core 10/10 passed after schema/type fixes.

## Phase 7 - Replay and Admission

- Added 12 fixtures across allow/warn/ask/block/injection/sensitive-egress/authorization/provenance/error/ordering/status scenarios.
- 240 replay requests: 12/12 scenarios passed, 100% availability, 0 timeout/error, p95 68.18ms, p99 98.99ms.
- Every BLOCK included current-step evidence; history-only risk produced WARN.
- Generated machine-readable and Markdown replay and Shadow statistics reports.
- Historical development Shadow data retains one Phase 5 cold-start timeout; it is not deleted or hidden.
- User instruction to continue through task completion is treated as approval to enter Phase 8 after the replay gate passed.

## Phase 8 - Enforce Mode

- Added runtime orchestrator, method mapper, decision combiner, safety floor, and legacy adapter.
- Python waits before PostgreSQL transactions; no transaction waits on the Worker.
- Local Core runs in enforce mode and persists optional engine metadata.
- Enforce smoke 14/14 passed; sensitive-read to external-network chain is upgraded from legacy ASK to method BLOCK.
- Separate legacy-mode process returned legacy ALLOW without starting a Worker.
- Killing the live Worker caused the current request to return `engine=legacy`; automatic restart restored method availability.

## Phase 9 - Method Graph and Core v2 Cleanup

- `/v1/runs/:runId/risk-graph` now prefers the latest successful method graph and reports `graph_source=method` plus evaluation ID.
- Old runs retain the compatible linear graph with `graph_source=legacy_linear`.
- Web graph adapter accepts method node/edge vocabulary and target resources.
- README, STARTUP, Core API, and method-engine README document Core v2 modes and lifecycle.
- Live verification: method graph 11 nodes/13 edges; legacy demo run 5 nodes/4 edges.
- Core enforce smoke 14/14 passed; Core/Web/Gateway services remain active.

## Final Validation

- Plugin: typecheck/build passed; 9 test files and 35/35 tests passed.
- Core: typecheck/build passed; 5 test files and 13/13 tests passed; database 14/14; smoke 14/14.
- Python: 38/38 tests passed.
- Replay: 12/12 fixtures and 240/240 requests passed; availability 100%; no timeout or protocol error.
- Web: typecheck/build/smoke passed.
- Runtime: Core healthy with PostgreSQL connected; method mode `enforce` available with an empty queue; Web HTTP 200; OpenClaw event loop healthy.
- Real OpenClaw commands: public README read completed, `.env` read was blocked, and `traceshield_status` completed with zero tool failures.
- Database correlation: each real run/step has exactly one tool-call row and one result row; before/after share the OpenClaw tool ID and stable `step_seq=1`; raw payload/result columns remain null.

### Final Defect Found and Fixed

The first real `traceshield_status` call was classified as an unknown tool and returned ASK without an approval route. Registry v2 now maps it to low-risk `status_read`, and the default intent frame permits that action. The replay fixture and a second real OpenClaw call both return ALLOW successfully.
