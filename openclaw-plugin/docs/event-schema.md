# TraceShield Event Schema v1

本文档定义 TraceShield OpenClaw 插件异步上报给 Core 的标准事件结构。

## TraceEvent

| 字段           | 类型             | 必填 | 用途                                            |
| -------------- | ---------------- | ---- | ----------------------------------------------- |
| event_id       | string           | 是   | 事件唯一 ID，用于 Core 侧幂等去重。             |
| schema_version | "v1"             | 是   | 事件结构版本，当前固定为 v1。                   |
| type           | TraceEventType   | 是   | 标识事件来自消息、模型、工具或降级决策阶段。    |
| timestamp      | number           | 是   | Unix 毫秒时间戳。                               |
| plugin_id      | string           | 是   | 插件实例 ID。                                   |
| gateway_id     | string           | 否   | 网关或宿主实例 ID，用于多实例定位。             |
| session_id     | string           | 是   | OpenClaw 会话 ID。                              |
| run_id         | string           | 是   | 单次 Agent 运行 ID。                            |
| trace_id       | string           | 是   | 链路 ID，用于串联一次任务中的消息、工具和决策。 |
| mode           | "sync" / "async" | 是   | 事件产生模式。异步事件不阻塞 OpenClaw。         |
| payload        | object           | 是   | 事件载荷，必须先经过脱敏、摘要或哈希处理。      |

## TraceEventType

| 类型              | 含义                                             |
| ----------------- | ------------------------------------------------ |
| message_received  | 收到用户或外部输入消息。                         |
| llm_input         | 发送给模型的输入。                               |
| llm_output        | 模型返回的输出。                                 |
| message_sending   | 即将发送给用户或外部系统的消息。                 |
| before_tool_call  | 工具调用前事件。同步审计时也会生成对应审计请求。 |
| after_tool_call   | 工具调用完成后的结果事件。                       |
| agent_end         | Agent 本轮任务结束。                             |
| fallback_decision | Core 不可用时插件本地降级策略产生的决策。        |

## 采集原则

1. 默认不上传完整敏感原文。
2. 大文本只保留 preview、hash 和 summary。
3. 文件内容默认不进入 payload。
4. 工具结果默认只上传摘要。
5. 所有事件必须携带 `schema_version`。
