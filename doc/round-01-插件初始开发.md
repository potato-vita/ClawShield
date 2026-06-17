# Round 01 — 插件初始开发（原第 0-9 轮）

## 时间

2026-06-17

## 概述

按照根目录《TraceShield OpenClaw 插件多轮执行计划》完成 10 轮初始开发，从数据契约到演示脚本，一次性完成插件最小闭环。

## 第 0 轮：数据契约

定义插件与 Core 的通信格式。

**产物：**
- `src/types/event.ts` — TraceEvent、AuditRequest 类型
- `src/types/decision.ts` — AuditDecision、AuditApproval 类型
- `src/types/config.ts` — PluginConfig 类型与默认值
- `docs/plugin-contract.md`
- `docs/event-schema.md`
- `docs/decision-schema.md`

## 第 1 轮：插件骨架

搭建 TypeScript ESM 项目，让 OpenClaw 能识别和加载插件。

**产物：**
- `package.json`、`tsconfig.json`、`openclaw.plugin.json`
- `src/index.ts` — 插件入口（初版为 activate/deactivate 模式）
- `src/config.ts` — 三级配置加载（getter → 属性 → 环境变量）
- `src/logger.ts` — 结构化 JSON 日志

## 第 2 轮：消息类 Hook

让插件能"看见"对话。

**产物：**
- `src/hooks/messageHooks.ts` — 注册 message_received、llm_input、llm_output、message_sending、agent_end
- `src/events/normalizeMessage.ts` — 统一生成 v1 TraceEvent
- `src/queue/memoryQueue.ts` — 内存队列，支持幂等去重

## 第 3 轮：工具调用 Hook

让插件能"看见"工具调用参数和结果。

**产物：**
- `src/hooks/toolHooks.ts` — 注册 before_tool_call、after_tool_call
- `src/events/normalizeToolCall.ts` — 提取工具名、类别、参数摘要、资源提示、风险提示（9 种 risk_hint）
- `src/events/normalizeToolResult.ts` — 记录结果 preview、hash、摘要

## 第 4 轮：Mock Core + 同步审计客户端

让插件真的能问 Core"这个工具调用能不能执行"。

**产物：**
- `src/client/auditClient.ts` — HTTP POST /v1/audit/tool-call，AbortController 超时
- `mock-core/server.ts` — 模拟审计服务，规则覆盖 rm -rf、.env、id_rsa、外部 URL、普通只读、默认 WARN

**验证：** Mock Core 对 `rm -rf` 返回 BLOCK。

## 第 5 轮：决策映射

把 Core 决策转换成 OpenClaw 能执行的结果。

**产物：**
- `src/policy/decisionMapper.ts`
  - ALLOW → 不干预
  - WARN → 放行但记录 warning
  - ASK → requireApproval
  - BLOCK → block: true + blockReason
  - modified_params → 替换参数后放行

**验证：** `decision-mapping.test.ts` 覆盖全部 5 种映射。

## 第 6 轮：异步事件队列与失败补传

消息、工具结果、任务结束等异步事件不能丢。

**产物：**
- `src/client/eventClient.ts` — POST /v1/events/batch
- `src/queue/diskQueue.ts` — 原子写（.tmp → rename），按 event_id 落盘
- `src/worker/flushWorker.ts` — 定时批量 flush，Core 不可用时落盘，恢复后补传

## 第 7 轮：脱敏与最小采集

避免插件自己变成隐私泄露源。

**产物：**
- `src/sanitizer/redact.ts` — 覆盖 token、api key、password、secret、cookie、private key
- `src/sanitizer/hash.ts` — SHA-256
- `src/sanitizer/preview.ts` — 长文本截断 500 字
- debug_full_payload 默认关闭

**验证：** `sanitizer.test.ts` 覆盖敏感字段脱敏和长文本截断。

## 第 8 轮：Core 故障本地降级

Core 断了插件也不能全放行。

**产物：**
- `src/policy/fallbackPolicy.ts`
  - 高风险工具 → fail-closed (BLOCK)
  - 敏感文件读取 → BLOCK
  - 低风险只读 → 仅本地 allow cache 命中才放行
  - 未知工具 → ASK
  - 所有 fallback 决策带 fallback_used: true
- `src/policy/localPolicyCache.ts` — 内存缓存，key = tool_kind:resource_hint

**验证：** `fallback-policy.test.ts` 覆盖高危阻断、敏感读取阻断、缓存放行、未知审批。

## 第 9 轮：测试与演示

让插件可以稳定演示。

**产物：**
- `src/tests/plugin-contract.test.ts`
- `src/tests/decision-mapping.test.ts`
- `src/tests/sanitizer.test.ts`
- `src/tests/fallback-policy.test.ts`
- `docs/demo-script.md`
- `docs/plugin-test-report.md`

**验证结果：**
```text
✓ TypeScript 类型检查：通过
✓ 单元测试：15/15 通过
✓ 构建 tsc：通过
✓ Mock Core /v1/audit/tool-call ：返回 BLOCK（curl 验证）
```

## 第 0-9 轮产物总览

```
openclaw-plugin/
  package.json, tsconfig.json, openclaw.plugin.json
  src/
    index.ts              # 插件入口
    config.ts             # 配置加载
    logger.ts             # 结构化日志
    types/                # event.ts, decision.ts, config.ts, hook.ts
    hooks/                # messageHooks.ts, toolHooks.ts
    events/               # normalizeMessage.ts, normalizeToolCall.ts, normalizeToolResult.ts, context.ts
    client/               # auditClient.ts, eventClient.ts
    queue/                # memoryQueue.ts, diskQueue.ts
    worker/               # flushWorker.ts
    sanitizer/            # redact.ts, hash.ts, preview.ts
    policy/               # decisionMapper.ts, fallbackPolicy.ts, localPolicyCache.ts
    utils/                # id.ts
    tests/                # 4 个测试文件, 15 个用例
    demo/                 # openclawDemo.ts
    docs/                 # 6 个文档
mock-core/
  server.ts               # /v1/audit/tool-call + /v1/events/batch
```
