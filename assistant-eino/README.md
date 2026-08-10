# TraceShield Assistant (CloudWeGo Eino)

This service is the read-only conversational backend for TraceShield's Security Assistant. It uses the CloudWeGo Eino `ChatModel` interface and the Eino OpenAI extension to call DeepSeek's OpenAI-compatible Chat Completions API. No tools are registered in this phase.

## Requirements

- Go 1.22+
- A DeepSeek API key

Pinned direct dependencies:

- `github.com/cloudwego/eino v0.9.13`
- `github.com/cloudwego/eino-ext/components/model/openai v0.1.13`

## Run

From this directory:

```bash
TRACESHIELD_ASSISTANT_API_KEY_FILE=/absolute/path/to/api-key go run ./cmd/server
```

The service listens on `127.0.0.1:8790` by default. Environment variables and limits are documented in `.env.example`. `TRACESHIELD_ASSISTANT_API_KEY` takes precedence over `DEEPSEEK_API_KEY`, and either environment key takes precedence over `TRACESHIELD_ASSISTANT_API_KEY_FILE`.

DeepSeek V4 thinking is disabled by default for lower demonstration latency. Set `TRACESHIELD_ASSISTANT_THINKING_ENABLED=true` to enable it.

## API

Health:

```bash
curl -s http://127.0.0.1:8790/health
```

Streaming chat:

```bash
curl -N http://127.0.0.1:8790/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-1","message":"Explain why this tool call was blocked.","history":[],"context":{"decision":"BLOCK"}}'
```

The stream emits `start`, zero or more `delta`, and `done` events. Validation and provider failures use an `error` event with a stable code and sanitized message.

## Test

```bash
go test ./...
```
