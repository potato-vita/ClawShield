# ClawShield Agent Rules

## Project Goal

Build ClawShield incrementally across 10 rounds, from bootstrap to competition-ready demo.

## Round 1 Scope

- Create stable repository skeleton
- Keep implementation minimal and explicit
- Prioritize startup correctness and clear module boundaries

## Do

- Keep route, service, model, and config responsibilities separate
- Mark unfinished behavior with TODO or explicit placeholders
- Keep naming aligned with architecture and spec docs

## Do Not

- Do not implement advanced business logic early
- Do not hardcode complex assumptions about OpenClaw behavior
- Do not merge runtime side effects into core policy logic
- Do not hide errors with empty exception handlers

## Code Quality Baseline

- Use clear names
- Keep modules focused
- Avoid duplicate logic
- Add concise comments where behavior is not obvious

## Handoff Contract

Every round should leave:

1. clear runnable result
2. explicit TODO boundaries
3. stable inputs for next round
