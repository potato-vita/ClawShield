# Known Limits

## Runtime / Integration

1. OpenClaw bridge defaults to local managed placeholder process in demo mode.
2. Tool executors are controlled/mock style; production-grade real side effects need extra hardening.
3. Current scenario set focuses on three canonical risk chains; long-tail chains need additional rule packs.
4. `exec` command parsing uses heuristic inference, so highly obfuscated commands may not map to expected action types.

## Policy / Semantics

1. Task type inference is keyword based for the current guardrail profile.
2. Policy explain output is optimized for demo clarity, not full compliance report depth.
3. Cross-session and cross-run correlation is intentionally limited in this version.

## UI / Report

1. Report page is optimized for narrative clarity; full raw event detail is in Run Detail page.
2. Graph view emphasizes highlighted risk paths and summary instead of full graph exploration tooling.

## Operational

1. SQLite is used for local reproducibility; concurrent high-load deployment needs a production database.
2. No distributed tracing system is integrated yet; logging is structured but process-local.
