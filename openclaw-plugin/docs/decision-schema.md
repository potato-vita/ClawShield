# TraceShield Decision Schema v1

本文档定义 Core 返回给 TraceShield OpenClaw 插件的同步审计决策。

## AuditDecision

| 字段 | 类型 | 必填 | 用途 |
| --- | --- | --- | --- |
| decision | ALLOW / WARN / ASK / BLOCK | 是 | 插件需要执行的审计动作。 |
| risk_level | low / medium / high / critical | 是 | 风险等级，用于展示、日志和降级参考。 |
| reason | string | 是 | 简短原因，不应包含敏感原文。 |
| matched_rules | string[] | 是 | 命中的策略规则 ID。 |
| policy_version | string | 否 | Core 策略版本。 |
| evidence_refs | string[] | 否 | Core 侧证据引用，插件不保存完整证据。 |
| modified_params | object / null | 否 | 修改后的工具参数，存在时插件尝试替换参数后放行。 |
| approval | AuditApproval / null | 否 | ASK 决策需要的人工确认信息。 |
| fallback_used | boolean | 否 | 是否由插件本地降级策略产生。 |

## 决策语义

| 决策 | 插件行为 |
| --- | --- |
| ALLOW | 放行工具调用，不额外干预。 |
| WARN | 放行工具调用，同时记录 warning 事件。 |
| ASK | 触发人工确认，按审批结果决定是否继续。 |
| BLOCK | 阻断工具调用，并向用户展示简短阻断原因。 |

## AuditApproval

| 字段 | 类型 | 必填 | 用途 |
| --- | --- | --- | --- |
| approval_id | string | 是 | 审批请求 ID。 |
| title | string | 是 | 审批标题。 |
| description | string | 是 | 审批描述。 |
| default_action | ALLOW / BLOCK | 是 | 超时后的默认动作。 |
| timeout_ms | number | 是 | 审批等待超时时间，单位毫秒。 |

## 降级策略要求

Core 超时或不可用时，插件必须启用本地保守策略：

1. 高风险工具默认 fail-closed。
2. 低风险只读工具只有命中本地 allow cache 才放行。
3. 未知工具默认 ASK 或 BLOCK。
4. 所有降级决策必须带 `fallback_used: true`。
