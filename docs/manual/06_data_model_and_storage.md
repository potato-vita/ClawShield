# 06 数据库与数据模型

## 6.1 数据存储基线

当前默认数据库：SQLite（`data/clawshield.db`）。

ORM：SQLAlchemy 2.x。

## 6.2 主表说明

### `runs`

用途：run 生命周期与最终风险结论。

关键字段：

- `run_id`（唯一业务 ID）
- `session_id`
- `task_summary`
- `task_type`
- `status`
- `final_risk_level`
- `disposition`
- `started_at` / `ended_at`
- `created_at` / `updated_at`

### `tasks`

用途：记录原始输入任务。

关键字段：

- `task_id`
- `run_id`
- `user_input`
- `source`
- `metadata`（JSON）

### `audit_events`

用途：系统事实事件流，是 timeline/graph/report 的事实源。

关键字段：

- `event_id`
- `run_id`
- `event_type` / `event_stage`
- `tool_id`
- `resource_type` / `resource_id`
- `semantic_decision` / `policy_decision`
- `risk_level` / `disposition`
- `status`
- `ts`

### `risk_hits`

用途：run 级风险链命中持久化。

关键字段：

- `run_id`
- `rule_id`（链 ID）
- `rule_type`
- `risk_level`
- `explanation`

### `evidence_edges`

用途：证据图边（可扩展为离线图分析输入）。

### `audit_reports`

用途：报告快照实体（当前报告主要实时组装）。

## 6.3 主键与业务 ID 策略

- 数据库层使用 `id` 自增主键。
- 业务 ID 由 `app/core/ids.py` 生成：
- `run_*`
- `task_*`
- `evt_*`

## 6.4 索引与查询特征

当前查询热点：

- run 详情：按 `run_id`。
- 事件查询：按 `run_id` + 时间排序，可附加 event_type/risk/tool/resource 过滤。
- session 追踪：按 `session_id` 取最新 run（callback 场景）。

## 6.5 一致性原则

- 报告数据由事件流导出，不在多个位置维护同一事实。
- run 状态由事件推进，而不是 UI 端主动维护。
- 风险结论由 analyzer 计算后回写 run，作为汇总视图。

## 6.6 数据保留建议（扩展项）

当前版本未实现自动归档策略。建议后续定义：

- 事件表 TTL（如 30/90 天）。
- 报告快照保留策略。
- 风险命中长期留存策略。

