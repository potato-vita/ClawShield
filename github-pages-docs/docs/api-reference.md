# API 参考

统一前缀：`/api/v1`

统一响应：

```json
{
  "success": true,
  "message": "ok",
  "data": {},
  "error": null
}
```

错误时：`success=false`，并包含 `error.error_code` 与 `error.details`。

## 健康与系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/system/start` | 启动系统与可选 OpenClaw 托管 |
| POST | `/system/stop` | 停止托管 OpenClaw |
| GET | `/system/status` | 返回 ClawShield/OpenClaw/Guardrails 状态 |

## 任务与运行

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/tasks/ingest` | 创建 run/task |
| GET | `/runs` | 最近 run 列表 |
| GET | `/runs/{run_id}` | run 详情 |

## 事件、图、报告

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/events` | 按条件查询事件 |
| GET | `/runs/{run_id}/timeline` | 时间线 |
| GET | `/runs/{run_id}/graph` | 证据图与高亮路径 |
| GET | `/runs/{run_id}/report` | 完整审计报告 |

## 策略与看板

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/rules/summary` | 规则计数摘要 |
| GET | `/dashboard/overview` | Dashboard 聚合数据 |
| POST | `/dashboard/scenarios/{scenario_id}/run` | 一键执行标准场景 |

## OpenClaw Bridge（核心）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/bridge/opencaw/session/bootstrap` | 建立或复用会话 run |
| POST | `/bridge/opencaw/tool-call` | 标准工具调用入口 |
| POST | `/bridge/opencaw/tool-result` | 标准工具结果入口 |
| POST | `/bridge/opencaw/callback/tool-call` | 回调版工具调用（兼容多 payload） |
| POST | `/bridge/opencaw/callback/tool-result` | 回调版工具结果 |
| POST | `/bridge/opencaw/callback/message` | 回调版消息事件 |

## UI 页面入口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/ui/dashboard` | 首页看板 |
| GET | `/ui/runs/{run_id}` | Run Detail |
| GET | `/ui/runs/{run_id}/report` | Audit Report |

## 常见错误码

- `RUN_NOT_FOUND`
- `RUN_NOT_FOUND_FOR_SESSION`
- `TOOL_CALL_PIPELINE_ERROR`
- `TOOL_RESULT_FAILED`
- `CALLBACK_TOOL_CALL_FAILED`
- `CALLBACK_TOOL_RESULT_FAILED`
- `CALLBACK_MESSAGE_FAILED`
- `DASHBOARD_SCENARIO_RUN_FAILED`
- `REPORT_BUILD_FAILED`
