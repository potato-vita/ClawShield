# TraceShield Eino Frontend

This application is built inside the vendored CloudWeGo Eino source tree. It uses an Eino `compose.Chain` to fetch TraceShield Core context and synthesize database-backed security analysis.

Round 01 起接入真实 ChatModel（火山云方舟 Ark，OpenAI 兼容协议，实现为 `model.BaseChatModel`）。配置 `ARK_*` 环境变量后，`/api/analysis` 由 LLM 生成中文安全分析；未配置或调用失败时自动回退到确定性答案（`Mode = "fallback"`）。

## Architecture

```text
Browser :8080 -> Eino workflow -> TraceShield Core :8000 -> SQLite
             \-> /core/* reverse proxy -------------------^
```

## Run

Start Core first:

```bash
cd core
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then start the Eino application:

```bash
cd eino
go run ./examples/traceshield
```

Open http://127.0.0.1:8080/.

Environment variables:

- `TRACESHIELD_CORE_URL`, default `http://127.0.0.1:8000`
- `TRACESHIELD_EINO_PORT`, default `8080`
- `ARK_API_KEY` / `ARK_CHAT_MODEL`（endpoint id，如 `ep-...`）/ `ARK_BASE_URL`（默认 `https://ark.cn-beijing.volces.com/api/v3`）：火山云方舟 ChatModel。二者同时非空才启用；可选 `ARK_EMBEDDING_MODEL`。凭证见根目录 `api.md`（测试用，勿提交）。

## Test

```bash
cd eino
go test ./examples/traceshield
```
