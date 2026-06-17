# TraceShield OpenClaw 插件多轮执行计划

## 1. 当前阶段目标

本阶段只设计和开发 **OpenClaw 插件部分**，不展开 TraceShield Core 的完整实现，也不做 Eino 前端。Core 在插件开发阶段先用 `mock-core` 模拟，只负责返回 `ALLOW / WARN / ASK / BLOCK` 四类审计结果。

插件阶段的核心目标是跑通下面这条链路：

```text
看见消息
  -> 看见工具调用
  -> 规范化事件
  -> 发给 Core / Mock Core
  -> 收到审计决策
  -> 放行 / 阻断 / 审批 / 改参
  -> 本地留痕
  -> 异步补传
```

第一阶段不要追求完整安全平台。只要插件能完成 **同步审计、危险阻断、事件采集、脱敏、本地降级**，就已经具备项目展示和后续扩展的基础。

## 2. 插件职责边界

OpenClaw 插件只负责执行面，也就是“看见并拦住”。它不直接写数据库，不维护完整风险图，也不承担复杂审计逻辑。

插件负责：

```text
1. 接入 OpenClaw Hook
2. 采集消息、模型输入输出、工具调用和工具结果
3. 将原始事件统一转换成 TraceShield Event
4. 在 before_tool_call 阶段同步请求 Core 审计
5. 将 Core 返回结果映射为 OpenClaw 的放行、阻断、审批或改参
6. 对异步事件进行本地队列缓存和失败补传
7. 对敏感内容进行脱敏、摘要和哈希处理
8. Core 不可用时执行本地保守策略
```

插件不负责：

```text
1. 不直接连接数据库
2. 不实现完整风险图分析
3. 不负责最终审计报告生成
4. 不参与 Eino 自然语言交互
5. 不保存完整敏感原文
```

## 3. 推荐目录结构

```text
traceshield/
  openclaw-plugin/
    package.json
    tsconfig.json
    openclaw.plugin.json
    src/
      index.ts
      config.ts
      logger.ts
      types/
        event.ts
        decision.ts
        config.ts
      hooks/
        messageHooks.ts
        toolHooks.ts
      events/
        normalizeMessage.ts
        normalizeToolCall.ts
        normalizeToolResult.ts
      client/
        auditClient.ts
        eventClient.ts
      queue/
        memoryQueue.ts
        diskQueue.ts
      worker/
        flushWorker.ts
      sanitizer/
        redact.ts
        hash.ts
        preview.ts
      policy/
        fallbackPolicy.ts
        localPolicyCache.ts
      tests/
        decision-mapping.test.ts
        sanitizer.test.ts
        fallback-policy.test.ts
    docs/
      plugin-contract.md
      event-schema.md
      decision-schema.md
      demo-script.md
      plugin-test-report.md

  mock-core/
    package.json
    tsconfig.json
    server.ts
```

## 4. 核心事件与决策对象

### 4.1 TraceEvent

`TraceEvent` 用于异步上报消息、模型输入输出、工具结果和任务结束事件。

```ts
export interface TraceEvent {
  event_id: string;
  schema_version: "v1";
  type:
    | "message_received"
    | "llm_input"
    | "llm_output"
    | "message_sending"
    | "before_tool_call"
    | "after_tool_call"
    | "agent_end"
    | "fallback_decision";
  timestamp: number;
  plugin_id: string;
  gateway_id?: string;
  session_id: string;
  run_id: string;
  trace_id: string;
  mode: "sync" | "async";
  payload: Record<string, unknown>;
}
```

### 4.2 AuditRequest

`AuditRequest` 用于 `before_tool_call` 同步审计。

```ts
export interface AuditRequest {
  request_id: string;
  schema_version: "v1";
  session_id: string;
  run_id: string;
  trace_id: string;
  tool_call_id: string;
  tool_name: string;
  tool_kind: string;
  raw_params: Record<string, unknown>;
  param_summary: Record<string, unknown>;
  resource_hint?: string;
  risk_hint?: string;
  context: {
    user_goal?: string;
    recent_message_hashes?: string[];
    workspace_root?: string;
  };
}
```

### 4.3 AuditDecision

`AuditDecision` 是 Core 返回给插件的结果。

```ts
export interface AuditDecision {
  decision: "ALLOW" | "WARN" | "ASK" | "BLOCK";
  risk_level: "low" | "medium" | "high" | "critical";
  reason: string;
  matched_rules: string[];
  policy_version?: string;
  evidence_refs?: string[];
  modified_params?: Record<string, unknown> | null;
  approval?: {
    approval_id: string;
    title: string;
    description: string;
    default_action: "ALLOW" | "BLOCK";
    timeout_ms: number;
  } | null;
  fallback_used?: boolean;
}
```

## 5. 多轮执行计划

### 第 0 轮：确认插件边界和数据契约

目标：先定死插件与 Core 的通信格式，不急着写业务逻辑。

输出文件：

```text
openclaw-plugin/docs/plugin-contract.md
openclaw-plugin/docs/event-schema.md
openclaw-plugin/docs/decision-schema.md
openclaw-plugin/src/types/event.ts
openclaw-plugin/src/types/decision.ts
openclaw-plugin/src/types/config.ts
```

本轮要完成：

```text
1. 定义 TraceEvent
2. 定义 AuditRequest
3. 定义 AuditDecision
4. 定义 PluginConfig
5. 明确同步事件和异步事件
6. 明确 Core 不可用时的降级策略
```

验收标准：

```text
1. 能清楚说明插件向 Core 发送什么
2. 能清楚说明 Core 向插件返回什么
3. 每个字段都有用途说明
4. 所有事件都有 schema_version
```

给 Codex 的指令：

```text
请为 TraceShield OpenClaw 插件设计 TypeScript 类型和文档。
只实现插件侧数据契约，不实现 Core。
需要包含 TraceEvent、AuditRequest、AuditDecision、PluginConfig。
所有字段要带中文注释，输出 docs/plugin-contract.md 和 src/types/*.ts。
```

### 第 1 轮：搭建插件骨架

目标：让 OpenClaw 能识别和加载插件。

输出文件：

```text
openclaw-plugin/package.json
openclaw-plugin/tsconfig.json
openclaw-plugin/openclaw.plugin.json
openclaw-plugin/src/index.ts
openclaw-plugin/src/config.ts
openclaw-plugin/src/logger.ts
```

插件基础信息建议：

```text
id: traceshield-security-plugin
name: TraceShield Security Plugin
activation.onStartup: true
```

本轮要完成：

```text
1. 建立 TypeScript ESM 项目
2. 添加插件 manifest
3. 添加插件入口文件
4. 启动时读取配置
5. 启动时输出插件版本和 Core 地址
```

验收标准：

```text
1. 插件能被 OpenClaw 加载
2. 插件启动时能输出日志
3. 配置可以读取 Core 地址、超时时间、运行模式
4. 没有接入审计逻辑
```

给 Codex 的指令：

```text
请搭建 TraceShield OpenClaw 原生插件骨架。
要求 TypeScript ESM，包含 openclaw.plugin.json、package.json、tsconfig.json、src/index.ts。
插件启动时读取配置并输出启动日志。
不要实现审计逻辑。
```

### 第 2 轮：接入消息类 Hook

目标：插件先能看见对话，不做阻断。

优先接入：

```text
message_received
llm_input
llm_output
message_sending
agent_end
```

输出文件：

```text
openclaw-plugin/src/hooks/messageHooks.ts
openclaw-plugin/src/events/normalizeMessage.ts
openclaw-plugin/src/queue/memoryQueue.ts
```

本轮要完成：

```text
1. 注册消息类 Hook
2. 将 OpenClaw 原始消息转换成 TraceEvent
3. 给事件补齐 event_id、session_id、run_id、trace_id
4. 将事件写入内存队列
5. 暂时不请求 Core
```

验收标准：

```text
1. 用户消息能被采集
2. 模型输入输出能被采集
3. agent_end 能生成任务结束事件
4. 所有事件进入本地队列
5. 不影响 OpenClaw 正常回复
```

给 Codex 的指令：

```text
请实现 TraceShield 插件的消息类 Hook。
把 message_received、llm_input、llm_output、message_sending、agent_end 统一转换成 TraceEvent，并写入内存队列。
不要阻断任何行为。
```

### 第 3 轮：接入工具调用 Hook，但只观察

目标：插件能看见工具调用参数和工具执行结果。

接入：

```text
before_tool_call
after_tool_call
```

输出文件：

```text
openclaw-plugin/src/hooks/toolHooks.ts
openclaw-plugin/src/events/normalizeToolCall.ts
openclaw-plugin/src/events/normalizeToolResult.ts
```

工具调用事件至少包含：

```text
tool_call_id
tool_name
tool_kind
raw_params
param_summary
resource_hint
risk_hint
```

`risk_hint` 本地初筛建议：

```text
file_read
file_write
file_delete
shell_exec
network_request
message_send
plugin_install
state_change
unknown
```

本轮要完成：

```text
1. 注册 before_tool_call
2. 注册 after_tool_call
3. 提取工具名和工具参数
4. 生成参数摘要
5. 根据参数生成 risk_hint
6. 本轮只记录，不调用 Core，不阻断
```

验收标准：

```text
1. 能捕获工具名
2. 能捕获参数摘要
3. 能捕获工具执行结果
4. 不保存完整大文本
5. 不阻断任何工具调用
```

给 Codex 的指令：

```text
请实现 TraceShield 插件的工具调用 Hook。
before_tool_call 和 after_tool_call 都要转换成标准 TraceEvent。
本轮只观察和记录，不调用 Core，不阻断。
```

### 第 4 轮：实现 Mock Core 和同步审计客户端

目标：让插件真的能问 Core “这个工具调用能不能执行”。

新增文件：

```text
mock-core/server.ts
openclaw-plugin/src/client/auditClient.ts
```

Mock Core 暂时按简单规则返回：

```text
cmd 包含 rm -rf          -> BLOCK
cmd 包含 .env / id_rsa   -> BLOCK
url 非白名单             -> ASK
普通只读                 -> ALLOW
可疑但不严重             -> WARN
```

插件请求接口：

```text
POST /v1/audit/tool-call
```

返回示例：

```json
{
  "decision": "BLOCK",
  "risk_level": "critical",
  "reason": "尝试读取敏感文件",
  "matched_rules": ["secret_file_read"],
  "modified_params": null,
  "approval": null
}
```

本轮要完成：

```text
1. 实现 auditClient
2. 设置请求超时
3. 在 before_tool_call 中同步请求 Mock Core
4. 解析 ALLOW / WARN / ASK / BLOCK
5. 暂时只打印结果，不做最终阻断
```

验收标准：

```text
1. before_tool_call 会同步请求 Mock Core
2. Core 正常时能返回审计结果
3. Core 超时时插件能捕获错误
4. 400ms 左右超时可配置
```

给 Codex 的指令：

```text
请为 TraceShield 插件实现 auditClient，并添加一个 mock-core 服务。
before_tool_call 调用 POST /v1/audit/tool-call。
Mock Core 根据简单规则返回 ALLOW/WARN/ASK/BLOCK。
```

### 第 5 轮：实现真正的阻断、审批和改参映射

目标：插件把 Core 决策转换成 OpenClaw 能执行的结果。

映射关系：

```text
ALLOW -> 不干预
WARN  -> 不干预，但记录 warning 事件
ASK   -> 返回 requireApproval
BLOCK -> 返回 block: true + blockReason
MODIFY -> 替换 params 后放行
```

本轮要完成：

```text
1. 实现 decision mapper
2. BLOCK 时阻止工具执行
3. ASK 时触发审批
4. modified_params 存在时替换工具参数
5. WARN 时记录事件但放行
```

验收标准：

```text
1. 危险命令能被阻止
2. 审批型请求能进入 requireApproval
3. 改参能生效
4. 阻断原因对用户简洁
5. 完整证据仍交给 Core 保存
```

给 Codex 的指令：

```text
请实现 TraceShield 插件的决策映射。
把 AuditDecision 映射为 OpenClaw before_tool_call 返回值：
ALLOW/WARN 放行，ASK requireApproval，BLOCK block:true，MODIFY 替换参数。
补充单元测试。
```

### 第 6 轮：实现异步事件队列和失败补传

目标：消息、工具结果、任务结束等异步事件不能丢。

输出文件：

```text
openclaw-plugin/src/queue/diskQueue.ts
openclaw-plugin/src/client/eventClient.ts
openclaw-plugin/src/worker/flushWorker.ts
```

策略：

```text
1. 普通事件先进本地队列
2. 每 1 到 3 秒批量发送
3. Core 不可用时写入磁盘
4. 重新连接后补传
5. event_id 用于幂等去重
```

本轮要完成：

```text
1. 实现内存队列
2. 实现磁盘队列
3. 实现批量 flush
4. 实现失败重试
5. 实现 event_id 幂等
```

验收标准：

```text
1. Core 停掉后事件不丢
2. Core 恢复后能补传
3. 重复发送不会生成重复事件
4. 异步上报不阻塞 OpenClaw 执行
```

给 Codex 的指令：

```text
请为 TraceShield 插件实现异步事件队列。
支持内存队列、磁盘落盘、批量 flush、失败重试和 event_id 幂等。
不要让异步事件阻塞 OpenClaw 正常执行。
```

### 第 7 轮：加入脱敏和最小采集

目标：避免插件自己变成隐私和敏感信息风险。

输出文件：

```text
openclaw-plugin/src/sanitizer/redact.ts
openclaw-plugin/src/sanitizer/hash.ts
openclaw-plugin/src/sanitizer/preview.ts
```

默认规则：

```text
API Key -> 只保留 hash
token/password/secret -> [REDACTED]
长文本 -> 只保留前 500 字 preview
文件内容 -> 默认不上传原文
工具结果 -> 默认只上传摘要
私钥内容 -> 直接替换为 [REDACTED_PRIVATE_KEY]
```

本轮要完成：

```text
1. 实现文本脱敏
2. 实现对象参数递归脱敏
3. 实现内容哈希
4. 实现预览截断
5. 给 debug_full_payload 设置默认关闭
```

验收标准：

```text
1. .env 内容不会完整上传
2. token 不会进入日志
3. 私钥不会进入日志
4. 大文本不会完整进入事件
5. 可以通过配置打开 debug_full_payload，但默认关闭
```

给 Codex 的指令：

```text
请为 TraceShield 插件实现脱敏模块。
默认不上传完整敏感内容，只上传 hash、preview 和 summary。
覆盖 token、api key、password、secret、cookie、private key 等模式。
```

### 第 8 轮：实现 Core 故障时的本地策略

目标：真实环境里 Core 断了，插件也不能全放行。

故障策略：

```text
高危工具：fail-closed
低风险只读：命中本地 allow cache 才放行
未知工具：ASK 或 BLOCK
```

高危工具类型：

```text
shell_exec
file_write
file_delete
network_request
message_send
plugin_install
state_change
```

本轮要完成：

```text
1. 实现 fallbackPolicy
2. 根据 risk_hint 判断工具风险等级
3. Core 超时或不可用时进入 fallback
4. fallback 结果写入 fallback_decision 事件
5. 所有 fallback 决策带 fallback_used: true
```

验收标准：

```text
1. Core 断开时 rm -rf 不会执行
2. Core 断开时读取敏感文件不会执行
3. Core 断开时普通只读按缓存处理
4. 所有降级决策都有 fallback_used 标记
5. 失败原因能在后续审计中看到
```

给 Codex 的指令：

```text
请实现 TraceShield 插件的本地降级策略。
当 Core 超时或不可用时，高风险工具 fail-closed，低风险只读工具仅在本地策略缓存命中时放行。
所有 fallback 决策都要记录事件。
```

### 第 9 轮：测试和演示脚本

目标：让插件部分可以稳定演示。

测试文件：

```text
openclaw-plugin/src/tests/plugin-contract.test.ts
openclaw-plugin/src/tests/decision-mapping.test.ts
openclaw-plugin/src/tests/sanitizer.test.ts
openclaw-plugin/src/tests/fallback-policy.test.ts
```

演示场景：

```text
1. 正常读取项目 README -> ALLOW
2. 读取 .env -> BLOCK
3. 读取 ~/.ssh/id_rsa -> BLOCK
4. 执行 rm -rf -> BLOCK
5. 访问外部 URL -> ASK
6. Core 关闭后执行高危命令 -> BLOCK
7. Core 关闭后普通只读 -> 按缓存处理
8. 包含 token 的工具参数 -> 上传前脱敏
```

输出文档：

```text
openclaw-plugin/docs/demo-script.md
openclaw-plugin/docs/plugin-test-report.md
```

验收标准：

```text
1. 所有核心映射都有测试
2. 所有脱敏规则都有测试
3. Core 故障场景有测试
4. demo-script.md 可以直接用于答辩演示
```

给 Codex 的指令：

```text
请为 TraceShield 插件补充测试和演示脚本。
覆盖 ALLOW、WARN、ASK、BLOCK、Core 超时、本地降级、脱敏。
生成 docs/demo-script.md，写清楚每个演示步骤和预期结果。
```

## 6. 优先级建议

如果时间不够，优先完成下面几轮：

```text
第 0 轮：数据契约
第 1 轮：插件骨架
第 4 轮：Mock Core + 同步审计
第 5 轮：阻断 / 审批 / 改参
第 8 轮：故障降级
第 9 轮：演示脚本
```

这几轮完成后，插件就已经具备最小闭环：

```text
OpenClaw 发起工具调用
  -> TraceShield 插件拦截
  -> 请求 Core / Mock Core
  -> 返回 BLOCK
  -> 插件阻止危险行为
  -> 生成审计事件
```

## 7. 队员分工建议

如果是 5 人小组，可以这样分：

```text
A 同学：插件骨架、manifest、配置加载
B 同学：Hook 接入、事件规范化
C 同学：auditClient、Mock Core、决策映射
D 同学：异步队列、失败补传、本地降级
E 同学：脱敏、测试、演示文档
```

组长重点盯三个接口：

```text
1. TraceEvent 格式不能乱改
2. AuditRequest 格式不能乱改
3. AuditDecision 到 OpenClaw 返回值的映射必须稳定
```

## 8. 本阶段完成标志

插件阶段完成后，应当能演示：

```text
1. OpenClaw 正常对话时，插件能采集消息事件
2. OpenClaw 调用工具时，插件能采集工具调用事件
3. 工具调用前，插件能同步请求 Core
4. Core 返回 BLOCK 时，工具不会执行
5. Core 返回 ASK 时，进入人工确认
6. Core 返回 modified_params 时，插件能改参后放行
7. Core 不可用时，高危行为默认阻断
8. 敏感内容不会完整进入日志
```

一句话总结：

```text
本阶段不是做完整 TraceShield，而是先把 OpenClaw 插件做成一个可靠的运行时安全闸门。
```
