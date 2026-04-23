# 08 策略与风控说明

## 8.1 双层判定模型

ClawShield 的判定不是单一规则，而是双层：

1. 语义守卫层（Guardrails）
2. 策略引擎层（Policy Engine）

最终由网关合并决策。

## 8.2 语义守卫（Guardrails）

入口：`guardrails_service.evaluate_tool_call`

职责：

- 读取最近 task 上下文。
- 推断 task_type（例如 analysis/general）。
- 调用 guardrails action 给出 `semantic_decision` 与 `semantic_reason`。
- 记录 `task_classified`、`dialog_state_changed`、`semantic_check_completed` 等事件。

## 8.3 策略引擎（Policy Engine）

入口：`policy_engine.evaluate(task_type, tool_id, resource_type, resource_id)`。

评估步骤：

1. task 规则匹配（`task_tool_map.yaml`）
2. tool 关键词匹配（内置）
3. resource 规则匹配（`tool_resource_map.yaml` + `sensitive_resources.yaml`）

决策汇总规则：

- 任一 `deny` => `decision=deny`
- 否则任一 `warn` => `decision=warn`
- 否则 `allow`

## 8.4 匹配器说明

### Task matcher

- 分 task_type 的 allow/deny 清单。
- 不在 allow 清单内时给出 warn。

### Tool matcher

- 基于 token 而非简单子串匹配，减少误报。
- destructive 关键词可直接 deny。
- external 关键词可 warn。

### Resource matcher

- 匹配工具与资源类型后，按 glob 规则判定 path/url/key。
- denied pattern 命中优先 deny。
- 敏感资源规则命中可抬高风险等级（通常 warn）。

## 8.5 网关合并决策

`gateway_manager` 中合并语义与策略：

- 只要语义或策略任一 deny，则最终 deny。
- 否则任一 warn，则最终 warn。
- 否则 allow。

deny 时直接阻断执行；allow/warn 才进入 executor。

## 8.6 风险链分析（Risk Analyzer）

当前内置 3 条 canonical 风险链：

1. `chain_workspace_escape`
2. `chain_env_then_http`
3. `chain_analysis_high_risk_tool`

### chain_workspace_escape

条件：analysis 任务中访问 file 资源且路径越界（`../` 或绝对路径）。

### chain_env_then_http

条件：敏感环境变量读取后，在 10 分钟窗口内发生 http 访问。

### chain_analysis_high_risk_tool

条件：analysis 任务调用高风险关键词工具（shell/exec/plugin 等）。

## 8.7 最终风险结论

- `final_risk_level`: 命中链中最高等级。
- `final_disposition`: 任一链 deny 则 deny，否则 warn；无命中则 allow。
- `summary`: 可读文本摘要，用于报告页面。

## 8.8 扩展策略建议

- 新增规则优先走 YAML，不要把规则硬编码进 API 层。
- 高风险规则调整必须增加回归测试。
- explain 输出应保持“短、准、可审计”。

