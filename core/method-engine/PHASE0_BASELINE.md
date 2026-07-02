# Runtime Method Engine Phase 0 Baseline

## Baseline

- Date: 2026-07-02
- Integration branch: `feature/runtime-method-engine`
- Integration base: `frontend@c18ffc4590bacf957428d5bab3e032474945e89d`
- Supplied source: `TraceShield_Experiment-main/TraceShield_Experiment-main/`
- Source form: extracted directory; no ZIP file was present in the workspace
- Imported source package: `traceshield_experiment_core/`
- Imported destination: `core/method-engine/python/traceshield_method/method/`
- Python: `3.12.3`
- Virtual environment: `core/method-engine/.venv/` (not tracked)

## Source Integrity

The deterministic source-package hash is computed from every sorted relative file path and its SHA-256 digest.

```text
source package files: 32
source aggregate SHA-256: 11118c7d1d0bd397ec20d409e9fa513dd8790bb4ce88d23f5863605d12c0f698
imported package files: 32
imported aggregate SHA-256: 87aaf513088ceb46959f06cdd2edf457ce4437cbbaf7555d1ed46117785ad294
```

The aggregate hashes differ because the Python package prefix and README usage example changed. Verification performed during Phase 0 showed:

```text
all Python files after normalizing the import prefix: no diff
method-owned YAML files: byte-identical SHA-256 matches
evaluator/boundary/correlation/detector/state/risk-graph logic changes: none
```

The source tree did not contain a `LICENSE`, `NOTICE`, or `COPYING` file. See `SOURCE.md`.

## Included and Excluded Scope

Included:

- Complete `traceshield_experiment_core` method package
- Package-owned YAML configuration
- Original method README
- Focused method-core test
- Equivalent isolated evaluator, tool mapper, and trace state tests

Excluded:

- `data/`
- `experiments/`
- `paper/`
- `dataset_processors/`
- Legacy `sc_guard/`
- Dataset and experiment scripts
- `scikit-learn`
- `rich`

No Fastify route, Core service, PostgreSQL schema, OpenClaw plugin, or Web file changed.

## Dependency Baseline

Runtime direct dependencies:

```text
pydantic==2.13.4
PyYAML==6.0.3
```

Development direct dependency:

```text
pytest==9.1.1
```

Resolved environment:

```text
annotated-types==0.7.0
iniconfig==2.3.0
packaging==26.2
pluggy==1.6.0
pydantic==2.13.4
pydantic_core==2.46.4
Pygments==2.20.0
pytest==9.1.1
PyYAML==6.0.3
typing-inspection==0.4.2
typing_extensions==4.15.0
```

Exact resolved versions are stored in `requirements-runtime.lock` and `requirements-dev.lock`.

## Package Path Adjustments

Mechanical package rename:

```text
traceshield_experiment_core -> traceshield_method.method
```

Adjusted locations:

- Absolute imports inside copied method Python files
- Original method README import example
- Focused method-core test imports
- Three equivalent isolated tests, which previously imported legacy `sc_guard`
- Test configuration paths now point to package-owned `method/configs/`
- Legacy `ConsistencyEvaluator` test construction now uses the method package's `TraceShieldEvaluator` with named config paths

No evaluator, boundary, risk graph, detector, correlation, reporter, schema, or state behavior was changed.

## Test Results

### Original supplied method-core test

Command:

```bash
PYTHONPATH=TraceShield_Experiment-main/TraceShield_Experiment-main \
  core/method-engine/.venv/bin/python -m pytest -q \
  TraceShield_Experiment-main/TraceShield_Experiment-main/tests/test_traceshield_core.py
```

Result: `11 passed`.

### Imported isolated method suite

Command:

```bash
cd core/method-engine
.venv/bin/python -m pytest -q \
  tests/test_traceshield_core.py \
  tests/test_evaluator.py \
  tests/test_tool_mapper.py \
  tests/test_trace_state.py
```

Result: `29 passed`.

Import was also verified from outside the project working directory:

```text
traceshield_method.method.evaluator
```

### Existing OpenClaw plugin

Commands:

```bash
cd openclaw-plugin
npm run typecheck
npm test
npm run build
```

Result: typecheck passed, build passed, `31/31` tests passed.

`npm run format:check` still reports the pre-existing formatting issue in `src/demo/openclawDemo.ts`. Phase 0 did not modify that file.

### Existing Core

Commands:

```bash
cd core
npm run typecheck
npm run build
npm run db:check
npm run smoke
```

Result: typecheck/build/database check passed; 11/11 tables found, 4 policies found, smoke `12/12` passed.

### Existing Web

Commands:

```bash
cd web
npm run typecheck
npm run build
npm run smoke
```

Result: typecheck/build passed; frontend smoke passed.

## Implicit Path and Data Findings

Method core findings:

- Default configuration is resolved relative to `config.py`, so package-owned YAML files are required at runtime.
- No method-core Python module imports `data/`, `experiments/`, `paper/`, dataset processors, `scikit-learn`, or `rich`.
- The method core does not require experiment datasets for the focused tests.
- The bundled NeMo adapter template is retained, but NeMo itself is not a Phase 0 runtime dependency.

Test findings:

- `test_traceshield_core.py` directly targeted the new method package.
- The source `test_evaluator.py`, `test_tool_mapper.py`, and `test_trace_state.py` targeted legacy `sc_guard` and top-level `configs/`; equivalent isolated versions were adapted to the imported method package.

## Real Decision Chain Verification

The following protected paths have no diff from the integration base:

```text
core/src/
core/package.json
core/package-lock.json
openclaw-plugin/
web/
docker-compose.yml
deploy/
```

Therefore `/v1/audit/tool-call`, `auditService`, `policyEngine`, PostgreSQL schema, OpenClaw plugin behavior, and Web behavior remain unchanged.

## Phase 1 Candidate File List

Phase 1 has not started. Stable IDs and run-level `step_seq` are expected to require these exact existing files:

```text
openclaw-plugin/src/events/context.ts
openclaw-plugin/src/events/normalizeToolCall.ts
openclaw-plugin/src/events/normalizeToolResult.ts
openclaw-plugin/src/hooks/toolHooks.ts
openclaw-plugin/src/hooks/messageHooks.ts
openclaw-plugin/src/types/event.ts
openclaw-plugin/src/types/hook.ts
core/src/types/pluginContract.ts
core/src/routes/audit.ts
core/src/routes/events.ts
core/src/services/auditService.ts
core/src/services/eventIngestService.ts
core/src/db/schema.sql
```

Likely new files rather than added responsibilities in existing modules:

```text
openclaw-plugin/src/runtime/runContextRegistry.ts
openclaw-plugin/src/tests/run-context-registry.test.ts
core/src/db/migrations/<step-seq-migration>.sql
core/src/services/runLifecycleService.ts
```

Relevant existing tests to update or extend:

```text
openclaw-plugin/src/tests/integration.test.ts
openclaw-plugin/src/tests/plugin-contract.test.ts
openclaw-plugin/src/tests/shared-event-queue.test.ts
core/scripts/smoke_test.ts
```

The exact migration shape and ID allocation ownership must be approved before these files are edited.

## Post-Phase-0 Note

This document is the historical Phase 0 baseline. Subsequent approved phases changed the product integration around the imported package. In particular, runtime registry version `v2` adds an exact low-risk mapping for `traceshield_status`; therefore the current tool registry is no longer byte-identical to the source registry. No imported evaluator, boundary, correlation, detector, state, or risk-graph algorithm was rewritten.
