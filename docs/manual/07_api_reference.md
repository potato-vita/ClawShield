# 07 API 接口说明

## 7.1 统一响应结构

所有 API 返回统一信封：

```json
{
  "success": true,
  "message": "ok",
  "data": {},
  "error": null
}
```

失败时：

```json
{
  "success": false,
  "message": "...",
  "data": null,
  "error": {
    "error_code": "...",
    "details": {}
  }
}
```

## 7.2 核心错误码（高频）

- `RUN_NOT_FOUND`
- `VALIDATION_ERROR`
- `TASK_INGEST_FAILED`
- `TOOL_CALL_PIPELINE_ERROR`
- `TOOL_RESULT_FAILED`
- `REPORT_BUILD_FAILED`
- `SCENARIO_NOT_FOUND`
- `MISSING_RUN_CONTEXT`
- `RUN_NOT_FOUND_FOR_SESSION`

## 7.3 路由清单

### 健康与系统

- `GET /api/v1/health`
- `POST /api/v1/system/start`
- `POST /api/v1/system/stop`
- `GET /api/v1/system/status`

### 任务与运行

- `POST /api/v1/tasks/ingest`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`

### 事件与分析

- `GET /api/v1/events`
- `GET /api/v1/runs/{run_id}/timeline`
- `GET /api/v1/runs/{run_id}/graph`
- `GET /api/v1/runs/{run_id}/report`

### 策略与看板

- `GET /api/v1/rules/summary`
- `GET /api/v1/dashboard/overview`
- `POST /api/v1/dashboard/scenarios/{scenario_id}/run`

### OpenClaw bridge

- `POST /api/v1/bridge/opencaw/session/bootstrap`
- `POST /api/v1/bridge/opencaw/tool-call`
- `POST /api/v1/bridge/opencaw/tool-result`
- `POST /api/v1/bridge/opencaw/callback/tool-call`
- `POST /api/v1/bridge/opencaw/callback/tool-result`
- `POST /api/v1/bridge/opencaw/callback/message`

### UI 页面

- `GET /api/v1/ui/dashboard`
- `GET /api/v1/ui/runs/{run_id}`
- `GET /api/v1/ui/runs/{run_id}/report`

## 7.4 关键接口详解

### 7.4.1 `POST /tasks/ingest`

请求体：

```json
{
  "session_id": "sess_001",
  "user_input": "请分析仓库并总结风险",
  "source": "ui",
  "metadata": {}
}
```

返回要点：

- `run_id`
- `task_type`（初始通常为 `unknown`）
- `status`（初始 `created`）

### 7.4.2 `POST /bridge/opencaw/tool-call`

请求体（必须含 `run_id`）：

```json
{
  "run_id": "run_xxx",
  "tool_call_id": "call_1",
  "tool_id": "workspace_reader",
  "arguments": {"file_path": "../secret.txt"}
}
```

返回包含：

- `decision`（最终决策）
- `semantic_reason`
- `policy_reason`
- `execution_status`
- `resource_type/resource_id`
- `risk_level`
- `matched_rules`
- `explanations`

### 7.4.3 `POST /bridge/opencaw/callback/tool-call`

支持两类 payload：

- 直接字段：`session_id + tool_id + tool_call_id + arguments`
- OpenAI 风格：`message.tool_calls[]`

若无 `run_id`，会按 `session_id` 解析或自动创建 run。

动作识别规则（当前版本）：

- 优先读取结构化字段：`url / env_key / file_path`
- 对 `exec` 一类工具，会解析 `arguments.command/cmd/script` 文本
  - 含网络命令 + URL（如 `curl https://...`）=> `http`
  - 含环境变量引用（如 `${OPENAI_API_KEY}`）=> `env_read`
  - 含文件读取命令（如 `cat ./a.txt`）=> `file_read`

这套规则用于把外部回调统一映射为可审计的 `resource_type/resource_id`，从而保证风险链可计算。

### 7.4.4 `GET /events`

可选过滤参数：

- `run_id`
- `event_type`
- `risk_level`
- `tool_id`
- `resource_type`
- `limit`
- `offset`
- `order`（`asc` / `desc`）

### 7.4.5 `POST /bridge/opencaw/callback/message`

用途：接收纯聊天消息事件（不依赖 tool-call）。  
支持负载：

- `message`（字符串或对象）
- `messages`（对象数组，含 `role/content`）

最小示例：

```json
{
  "session_id": "oc_session_001",
  "messages": [
    {"role": "user", "content": "请先审阅代码结构"},
    {"role": "assistant", "content": "好的，我先看目录层级"}
  ]
}
```

返回包含：

- `run_id`
- `processed_count`
- 每条消息对应的审计事件摘要（`event_id/role/actor_type/content_preview`）

### 7.4.6 `GET /runs/{run_id}/report`

返回报告主结构：

- `task_summary`
- `semantic_summary`
- `tool_calls`
- `resources`
- `risk_hits`
- `timeline`
- `graph`
- `final_risk_level`
- `final_disposition`
- `disposition_summary`
- `conclusion`

## 7.5 API 设计注意事项

- API 层异常必须走统一错误协议。
- 不在 API 层做复杂业务逻辑分支。
- 新增接口前先评估是否可复用现有 service。
