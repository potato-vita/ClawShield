# 运行时流程

## 主流程：Tool Call 到报告

```text
Client/OpenClaw
  -> POST /bridge/opencaw/tool-call
    -> BridgeService.process_tool_call
      -> GuardrailsService.evaluate_tool_call
      -> infer_action_intent
      -> GatewayManager.execute
        -> PolicyEngine.evaluate
        -> Executor.execute (or blocked)
      -> Audit event persist
  -> GET /runs/{run_id}/graph
  -> GET /runs/{run_id}/report
```

## 流程分解

## 1) 任务摄入

- `POST /api/v1/tasks/ingest`
- 建立 `run` + `task`
- 写入事件：`task_received`、`run_created`

## 2) 工具调用（语义 + 策略 + 执行）

- 事件：`tool_call_requested`
- 语义判定：`semantic_check_completed`
- 策略判定：`policy_check_completed`、`risk_rule_matched`
- 资源请求：`resource_access_requested`
- 执行过程：`tool_execution_started`、`tool_execution_completed`

## 3) 工具结果回传

- `POST /api/v1/bridge/opencaw/tool-result`
- 事件：`tool_result_received`

## 4) 图与结论

- `GET /api/v1/runs/{run_id}/graph`
  - 输出 `nodes`、`edges`、`highlighted_paths`、`summary`
  - 事件：`risk_chain_formed`、`final_risk_conclusion_generated`
- `GET /api/v1/runs/{run_id}/report`
  - 聚合输出给 UI

## Run 状态推进

状态推进由 telemetry 收集器驱动，典型顺序如下：

- `created` -> `running` -> `finished`

当流程异常或缺失上下文时，统一通过 API 错误契约返回（`success=false` + `error_code`）。
