# TraceShield Runtime Method Engine

This directory contains the isolated Python method core and its local JSON Lines worker.

## Modes

- `legacy`: TypeScript policy only; no worker required.
- `shadow`: legacy controls execution while method results are recorded separately.
- `enforce`: method suggestion controls execution, elevated by the safety floor; worker failures fall back to legacy.

The worker is managed by Fastify Core over stdin/stdout and does not open a network port. Protocol output uses stdout exclusively; logs use stderr.

## Validation

```bash
.venv/bin/python -m pytest -q
cd ..
npm run method:health
npm run method:replay
npm run method:report
```

See `SOURCE.md`, `PHASE0_BASELINE.md`, and `doc/core-v2-runtime-method/` for provenance and phase reports.

