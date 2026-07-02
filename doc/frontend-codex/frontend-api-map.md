# TraceShield Frontend API Map

Base URL 由 `VITE_TRACESHIELD_CORE_BASE_URL` 控制，默认 `http://127.0.0.1:8787`。

| Frontend module | Core endpoint | Usage | Current compatibility |
|---|---|---|---|
| `api/dashboard.ts` | `GET /v1/dashboard/runtime-status` | 顶部指标 | 已实现 |
| `api/sessions.ts` | `GET /v1/audit/events?limit=200` | 派生 sessions/runs 和 Tool Calls | 已实现 |
| `api/runs.ts` | `GET /v1/runs/:runId/risk-graph` | Runtime Path | 已实现 |
| `api/runs.ts` | `GET /v1/runs/:runId/evidence-path` | Evidence Path | 已实现 |
| `api/toolCalls.ts` | `GET /v1/tool-calls/:id/decision` | 调用决策详情 | 已实现 |
| `api/coreStatus.ts` | `GET /v1/health` | Core/DB 健康状态 | 已实现 |
| `api/stream.ts` | `GET /v1/stream/audit-events` | audit/trace 实时事件 | 已实现，支持重连 |
| `api/policies.ts` | `GET/POST /v1/policies` | 策略列表/创建 | Core 尚未实现，mock fallback |
| `api/policies.ts` | `PATCH /v1/policies/:id` | 策略启停 | Core 尚未实现，mock fallback |

## 数据映射

Core 当前没有单独的 session/run 列表接口。前端将 `/v1/audit/events` 按 `session_id` 和 `run_id` 分组，生成会话、run 和 Tool Call 模型。选中 run 后再并行请求 graph 和 evidence。

Core 决策值映射：`BLOCK → block`、`ALLOW → allow`、`WARN/ASK/其他 → review`。风险级别限定为 `critical/high/medium/low`。

## 错误与 fallback

`api/client.ts` 统一使用 5 秒超时、HTTP 状态检查和 JSON 校验。Core 模式首次加载失败时，runtime store 进入 `fallback`，保留 mock 数据并显示错误条。SSE 错误独立降级为 Realtime Offline，不影响 HTTP 数据和页面交互。
