# 04 核心流程与时序

## 4.1 任务摄入流程（Task Ingest）

入口：`POST /api/v1/tasks/ingest`

主要步骤：

1. `task_service` 调用 `run_service.initialize_run` 创建 run。
2. 持久化 task。
3. 记录 `task_received` 与 `run_created` 事件。
4. 返回 `run_id`。

输出价值：

- 给后续 tool-call 提供稳定 run 上下文。
- 建立事件链起点。

## 4.2 工具调用流程（Tool Call）

入口：`POST /api/v1/bridge/opencaw/tool-call`

主要步骤：

1. 记录 `tool_call_requested` 事件。
2. `guardrails_service.evaluate_tool_call` 给出语义判定。
3. `bridge_service` 解析 action_type。
4. `gateway_manager.execute`：
5. interceptor 抽取资源。
6. policy engine 评估规则。
7. 记录 `policy_check_completed` / `risk_rule_matched` / `disposition_applied` / `resource_access_requested` 等事件。
8. 若 deny，直接返回阻断结果。
9. 若允许执行，调用 executor 并记录 `tool_execution_started`、`tool_execution_completed`。

## 4.3 工具结果流程（Tool Result）

入口：`POST /api/v1/bridge/opencaw/tool-result`

主要步骤：

1. 验证 run 是否存在。
2. 记录 `tool_result_received` 事件。
3. 返回接受结果（`accepted=true`）。

## 4.4 报告生成流程（Report）

入口：`GET /api/v1/runs/{run_id}/report`

主要步骤：

1. 拉取事件流。
2. 生成 timeline。
3. 构建 evidence graph。
4. 执行 risk analyzer（链式检测）。
5. 写回 run 的 `final_risk_level` 与 `disposition`。
6. `report_assembler` 汇总为前端友好结构。

## 4.5 OpenClaw callback 流程

入口：

- `/api/v1/bridge/opencaw/session/bootstrap`
- `/api/v1/bridge/opencaw/callback/tool-call`
- `/api/v1/bridge/opencaw/callback/tool-result`

关键点：

- callback 支持仅用 `session_id`，可自动解析/创建 run。
- tool-call 支持直接字段和 OpenAI 风格 `message.tool_calls`。
- tool-result 支持 `tool_result` 或 `tool_results` 批量结构。

## 4.6 run 状态推进规则

TelemetryCollector 映射：

- `task_received -> created`
- `task_classified/dialog_state_changed -> analyzing`
- `tool_call_requested -> tool_pending`
- `tool_execution_started -> executing`
- `tool_result_received -> finished`
- `disposition_applied + deny -> blocked`

说明：状态推进是单向的，避免在多事件混合下回退到旧状态。

## 4.7 典型事件类型清单

高频事件包括：

- `task_received`
- `run_created`
- `task_classified`
- `dialog_state_changed`
- `semantic_check_completed`
- `tool_call_requested`
- `policy_check_completed`
- `risk_rule_matched`
- `disposition_applied`
- `resource_access_requested`
- `tool_execution_started`
- `tool_execution_completed`
- `tool_result_received`
- `risk_chain_formed`
- `final_risk_conclusion_generated`

