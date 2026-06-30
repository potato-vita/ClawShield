# TraceShield Core API

Base URL: `http://127.0.0.1:8787`

All non-SSE endpoints accept and return JSON. Timestamps in plugin events are Unix milliseconds; timestamps returned from PostgreSQL are ISO 8601 strings.

## Health and dashboard

### `GET /health`

### `GET /v1/health`

Both return:

```json
{
  "ok": true,
  "version": "0.1.0",
  "db_connected": true
}
```

### `GET /v1/dashboard/runtime-status`

Returns real 24-hour aggregates:

```json
{
  "tool_calls_24h": 12,
  "blocked_24h": 3,
  "high_risk_24h": 3,
  "policy_hits_24h": 12
}
```

## Synchronous audit

### `POST /v1/audit/tool-call`

Request:

```json
{
  "request_id": "audit-1",
  "schema_version": "v1",
  "session_id": "session-1",
  "run_id": "run-1",
  "trace_id": "trace-1",
  "tool_call_id": "tool-1",
  "tool_name": "file_read",
  "tool_kind": "file_read",
  "raw_params": { "path": "README.md" },
  "param_summary": {},
  "resource_hint": "README.md",
  "risk_hint": "file_read",
  "context": {}
}
```

Response:

```json
{
  "decision": "ALLOW",
  "risk_level": "low",
  "reason": "No blocking policy matched this tool call.",
  "matched_rules": ["default_allow"],
  "policy_version": "v1",
  "evidence_refs": ["evidence-uuid"],
  "modified_params": null,
  "approval": null,
  "fallback_used": false
}
```

Decisions are `ALLOW`, `WARN`, `ASK`, or `BLOCK`. Reusing a `request_id` returns its existing decision rather than creating duplicate evidence.

Initial policy behavior:

- Sensitive file/private-key reads: `BLOCK critical`.
- Destructive shell commands (`rm -rf`, `mkfs`, `dd if=`): `ASK critical`; approval defaults to `BLOCK` and times out after 30 seconds.
- External network requests: `ASK medium` with approval metadata.
- Unknown tools: `WARN medium`.
- Other calls: `ALLOW low`.

## Asynchronous events

### `POST /v1/events/batch`

Request:

```json
{
  "events": [
    {
      "event_id": "event-1",
      "schema_version": "v1",
      "type": "message_received",
      "timestamp": 1782650000000,
      "plugin_id": "traceshield-security-plugin",
      "session_id": "session-1",
      "run_id": "run-1",
      "trace_id": "trace-1",
      "mode": "async",
      "payload": {
        "role": "user",
        "content": "sanitized preview",
        "content_hash": "hash"
      }
    }
  ]
}
```

Response:

```json
{
  "ok": true,
  "inserted": 1,
  "duplicated": 0,
  "message_extracted": 1,
  "tool_result_extracted": 0
}
```

`event_id` is idempotent. Message-like events are extracted to `messages`; `after_tool_call` is extracted to `tool_results`.

## Queries

### `GET /v1/audit/events?limit=50`

Returns `{ "events": [...], "limit": 50 }`. Limit range: 1–200.

### `GET /v1/tool-calls/:toolCallId`

Returns `{ "tool_call": {...} }` without raw parameters.

### `GET /v1/tool-calls/:toolCallId/decision`

Returns `{ "tool_call": {...}, "decision": {...} | null, "rule_hits": [...] }`.

### `GET /v1/runs/:runId/evidence-path`

Returns `{ "run_id": "...", "steps": [...] }` in evidence order.

### `GET /v1/runs/:runId/risk-graph`

Returns `{ "run_id": "...", "nodes": [...], "edges": [...] }`. The graph is generated at query time and is not persisted.

## Live stream

### `GET /v1/stream/audit-events`

Content type: `text/event-stream`. Event names:

- `connected`: connection acknowledgement.
- `audit_event`: emitted after a successful synchronous decision.
- `trace_event`: emitted once per newly inserted asynchronous event.
- Heartbeats are SSE comments sent every 15 seconds.

```bash
curl -N http://127.0.0.1:8787/v1/stream/audit-events
```

## Privacy switches

The following default to `false`:

- `TRACESHIELD_SAVE_RAW_PAYLOAD`
- `TRACESHIELD_SAVE_RAW_PARAMS`
- `TRACESHIELD_SAVE_RAW_RESULT`

Keep them disabled outside explicit local debugging. Query and SSE APIs do not expose raw parameters or raw event payloads.
