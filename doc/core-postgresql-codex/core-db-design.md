# TraceShield Core 数据库设计

TraceShield Core 使用 PostgreSQL 16，通过 `pgcrypto` 生成 UUID。Schema 在 `core/src/db/schema.sql`，可重复执行。

## 表用途

| 表 | 用途 | 主要幂等键/关联 |
| --- | --- | --- |
| `audit_sessions` | 会话首次/最近活动 | `session_id` |
| `audit_runs` | 一次 Agent run 与决策聚合 | `run_id` → session |
| `trace_events` | 异步事件主记录 | `event_id` |
| `messages` | 消息类事件结构化投影 | unique `event_id` |
| `tool_calls` | 工具调用、参数摘要与状态 | `tool_call_id`, unique `request_id` |
| `tool_results` | after-tool 结果投影 | unique `event_id` → tool call |
| `audit_decisions` | ALLOW/WARN/ASK/BLOCK 决策 | unique `request_id` → tool call |
| `audit_rule_hits` | 决策命中的策略明细 | unique decision + policy |
| `policies` | 策略种子、版本和开关 | `policy_id` |
| `evidence_items` | 某次决策的证据容器 | run/tool/decision |
| `evidence_steps` | 有序的证据路径步骤 | evidence + `step_order` |

## 核心关系

```text
audit_sessions
  └─ audit_runs
       ├─ trace_events ── messages
       ├─ tool_calls ── tool_results
       │    └─ audit_decisions ── audit_rule_hits
       └─ evidence_items ── evidence_steps
```

## 安全与保留原则

- `raw_params`、`raw_payload`、`raw_result` 字段存在，但默认为 `NULL`。
- 结构化投影优先保存摘要、hash、已脱敏 preview 和必要元数据。
- check 约束限制决策、风险等级、事件类型和状态。
- 经常使用的 run/time、decision/time、policy/time 组合均有索引。

## 迁移与检查

```bash
cd core
cp .env.example .env
npm run db:migrate
npm run db:check
```

`db:check` 必须报告 11/11 张表且至少 4 条策略。
