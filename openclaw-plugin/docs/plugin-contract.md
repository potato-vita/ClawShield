# TraceShield OpenClaw 插件数据契约

本文档固定 TraceShield OpenClaw 插件与 Core / Mock Core 之间的 v1 通信契约。本阶段只实现插件侧数据契约，不实现 Core。

## 职责边界

插件负责：

1. 接入 OpenClaw Hook。
2. 采集消息、模型输入输出、工具调用和工具结果。
3. 将原始事件统一转换成 `TraceEvent`。
4. 在 `before_tool_call` 阶段同步请求 Core 审计。
5. 将 Core 返回结果映射为 OpenClaw 的放行、阻断、审批或改参。
6. 对异步事件进行本地队列缓存和失败补传。
7. 对敏感内容进行脱敏、摘要和哈希处理。
8. Core 不可用时执行本地保守策略。

插件不负责：

1. 不直接连接数据库。
2. 不实现完整风险图分析。
3. 不负责最终审计报告生成。
4. 不参与 Eino 自然语言交互。
5. 不保存完整敏感原文。

## 同步链路

`before_tool_call` 是同步审计点。插件必须在工具执行前构造 `AuditRequest`，请求 Core 的 `POST /v1/audit/tool-call`，并等待 `AuditDecision`。

同步链路用于决定是否放行工具调用，因此必须设置较短超时。默认超时时间为 400ms，可通过 `PluginConfig.audit_timeout_ms` 覆盖。

## 异步链路

消息、模型输入输出、工具结果、任务结束和降级决策通过 `TraceEvent` 异步上报。异步事件不得阻塞 OpenClaw 正常执行。

异步事件失败时先进入内存队列；Core 长时间不可用时落盘，后续恢复连接后按 `event_id` 幂等补传。

## AuditRequest

| 字段           | 类型   | 必填 | 用途                                       |
| -------------- | ------ | ---- | ------------------------------------------ |
| request_id     | string | 是   | 审计请求唯一 ID。                          |
| schema_version | "v1"   | 是   | 请求结构版本。                             |
| session_id     | string | 是   | 会话 ID。                                  |
| run_id         | string | 是   | 单次 Agent 运行 ID。                       |
| trace_id       | string | 是   | 链路 ID。                                  |
| tool_call_id   | string | 是   | OpenClaw 工具调用 ID。                     |
| tool_name      | string | 是   | 工具名称。                                 |
| tool_kind      | string | 是   | 工具类别，例如 shell_exec、file_read。     |
| raw_params     | object | 是   | 原始参数，仅用于同步审计，不进入普通日志。 |
| param_summary  | object | 是   | 参数摘要。                                 |
| resource_hint  | string | 否   | 文件路径、URL、命令目标等资源提示。        |
| risk_hint      | string | 否   | 本地风险提示。                             |
| context        | object | 是   | 用户目标、消息哈希、工作区根目录等上下文。 |

## TraceEvent

详见 `event-schema.md`。所有事件必须带 `schema_version: "v1"`，所有载荷必须遵守最小采集原则。

## AuditDecision

详见 `decision-schema.md`。Core 只能返回 `ALLOW`、`WARN`、`ASK`、`BLOCK` 四类主决策。参数改写通过 `modified_params` 表达，不新增主决策枚举。

## PluginConfig

| 字段                    | 类型                            | 默认值                      | 用途                                     |
| ----------------------- | ------------------------------- | --------------------------- | ---------------------------------------- |
| plugin_id               | string                          | traceshield-security-plugin | 插件 ID。                                |
| gateway_id              | string                          | 无                          | 网关或宿主实例 ID。                      |
| core_base_url           | string                          | http://127.0.0.1:8787       | Core / Mock Core 地址。                  |
| audit_timeout_ms        | number                          | 400                         | 同步审计超时时间。                       |
| event_flush_timeout_ms  | number                          | 1000                        | 异步事件上报超时时间。                   |
| event_flush_interval_ms | number                          | 2000                        | 异步事件批量上报间隔。                   |
| mode                    | development / demo / production | development                 | 插件运行模式。                           |
| fallback_enabled        | boolean                         | true                        | Core 不可用时是否启用本地策略。          |
| debug_full_payload      | boolean                         | false                       | 是否允许上传完整载荷，默认关闭。         |
| disk_queue_dir          | string                          | .traceshield/events         | 磁盘队列目录。                           |
| memory_queue_max_events | number                          | 1000                        | 内存队列最大事件数。                     |
| local_allow_tool_kinds  | string[]                        | ["file_read"]               | Core 故障时允许缓存放行的只读工具类别。  |
| high_risk_tool_kinds    | string[]                        | 见类型默认值                | Core 故障时必须 fail-closed 的工具类别。 |

## Core 不可用时的降级策略

当 Core 超时、网络失败或返回不可解析结果时，插件进入本地降级策略：

1. `shell_exec`、`file_write`、`file_delete`、`network_request`、`message_send`、`plugin_install`、`state_change` 默认阻断。
2. `file_read` 这类低风险只读工具必须命中本地 allow cache 才放行。
3. 未知工具默认 ASK；不支持审批时默认 BLOCK。
4. 每次本地决策都生成 `fallback_decision` 事件。
5. 降级决策必须设置 `fallback_used: true`，便于后续审计区分。
