# OpenClaw Callback Integration

This project now supports callback-based OpenClaw integration without requiring `run_id` in every event.

## Endpoints

- `POST /api/v1/bridge/opencaw/session/bootstrap`
- `POST /api/v1/bridge/opencaw/callback/tool-call`
- `POST /api/v1/bridge/opencaw/callback/tool-result`
- `POST /api/v1/bridge/opencaw/callback/message`

## Minimal Flow

1. Bootstrap session:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","user_input":"请分析仓库并总结风险"}'
```

2. Send tool-call:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/tool-call \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","tool_id":"workspace_reader","tool_call_id":"call_1","arguments":{"file_path":"../secret.txt"}}'
```

3. Send tool-result:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/tool-result \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","tool_result":{"tool_call_id":"call_1","tool_id":"workspace_reader","execution_status":"mock_completed","result_summary":"blocked"}}'
```

4. Send pure chat message events:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/callback/message \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"oc_session_001","messages":[{"role":"user","content":"请先审阅代码结构"},{"role":"assistant","content":"好的，我先看目录层级。"}]}'
```

5. View report:

```bash
xdg-open "http://127.0.0.1:8000/api/v1/ui/dashboard"
```

## Supported Tool-Call Payload Shapes

### Shape A: Direct fields

```json
{
  "session_id": "oc_session_001",
  "tool_call_id": "call_1",
  "tool_id": "workspace_reader",
  "arguments": {"file_path": "../secret.txt"}
}
```

### Shape B: OpenAI-style tool_calls

```json
{
  "session_id": "oc_session_001",
  "message": {
    "tool_calls": [
      {
        "id": "call_1",
        "function": {
          "name": "workspace_reader",
          "arguments": "{\"file_path\":\"../secret.txt\"}"
        }
      }
    ]
  }
}
```

## Notes

- `session_id` is enough for callback endpoints; `run_id` is optional.
- On first callback for a new `session_id`, ClawShield auto-creates a run.
- If OpenClaw can already attach `run_id`, you can still use existing:
  - `POST /api/v1/bridge/opencaw/tool-call`
  - `POST /api/v1/bridge/opencaw/tool-result`
- For generic `exec` tools, include `arguments.command` (or `cmd/script`).
  ClawShield will infer action type from command text:
  - env variable read -> `env_read`
  - network call with URL -> `http`
  - file read command -> `file_read`
