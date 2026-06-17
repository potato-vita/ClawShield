# Round 06 — 代码审查与关键修复

## 时间

2026-06-17

## 前置状态

第 0-13 轮已完成了任务书中定义的所有功能：插件骨架、消息/工具 Hook、Mock Core、同步审计、决策映射、异步队列、脱敏、降级策略、测试和演示脚本。类型检查、测试和构建均已通过。

## 本轮目标

对核心代码做系统性审查，修复发现的关键 bug 和架构问题，使代码达到可演示和可交付的质量标准。

## 审查方法

逐文件通读 `openclaw-plugin/src/` 下所有 27 个 TypeScript 源文件，按数据流追踪每条链路。发现的问题按严重程度分为严重/高/中/低四级，本轮优先修复严重和高优先级问题。

## 修复清单

### 🔴 严重：`redactText` 脱敏在截断之前 (redact.ts)

**问题**：`redactText(value)` 内部先调用 `previewText(value)` 把内容截断到 500 字符，再对截断后的文本做正则脱敏。出现在第 501 个字符之后的密钥/密码不会被脱敏。

**修复**：
- `redactText` 现在接受 `unknown` 类型，内部先序列化，再对完整文本执行脱敏正则（private key → API key → assignment secret），最后调用 `previewText` 截断
- `normalizeMessage.ts` 和 `normalizeToolResult.ts` 去掉了多余的 `previewText` 外层调用，避免双重截断
- 语义：**先脱敏，再截断**。即使敏感内容在 500 字符之后，也不会被遗漏

### 🟠 高：死代码清理 (toolHooks.ts / messageHooks.ts)

**问题**：`toolHooks.ts` 和 `messageHooks.ts` 导出了 `registerToolHooks()` 和 `registerMessageHooks()`，但 `index.ts` 完全不使用，所有 Hook 注册逻辑全内联在主文件中，造成维护歧义。

**修复**：
- 将 Hook 注册逻辑从 `index.ts` 提取到 `toolHooks.ts` 和 `messageHooks.ts`
- `index.ts` 现在通过调用 `registerMessageHooks()` 和 `registerToolHooks()` 完成 Hook 注册
- `index.ts` 只保留非 Hook 的插件基础设施：`traceshield_status` 工具、`flushWorker` 服务、`before_prompt_build` 安全提示、`agentToolResultMiddleware` 阻断反馈、`registerSecurityAuditCollector`
- 工具函数（`on()`、`asRecord()` 等）从 `index.ts` 和 Hook 模块中去除了重复

### 🟠 高：ID 生成改用 crypto.randomUUID() (id.ts)

**问题**：`createId()` 使用 `Math.random().toString(36)` 生成随机部分。`Math.random()` 不是密码学安全的，安全审计事件 ID 可预测意味着可能被伪造。

**修复**：改用 `crypto.randomUUID()`，截取前 8 位作为随机部分。格式保持 `{prefix}_{timestamp36}_{uuid8}`。

### 🟡 中：内存队列增加最大重试次数 (memoryQueue.ts)

**问题**：`requeue()` 每次递增 `attempts` 但没有上限，一个"有毒"事件会无限循环：dequeue → 发送失败 → requeue → 再次 dequeue。

**修复**：构造函数增加 `maxAttempts` 参数（默认 10），`requeue()` 超过上限的事件直接丢弃。

### 🟡 中：敏感读取检测覆盖 shell_exec (fallbackPolicy.ts)

**问题**：`isSensitiveRead()` 只检查 `tool_kind === "file_read"`。`shell_exec cat .env` 同样能读取敏感文件，但会跳过检测。

**修复**：
- 增加 `tool_kind === "shell_exec"` 的检查分支
- 增加 `/etc/shadow`、`/etc/passwd` 等系统敏感路径
- 增加正则检测 `cat` 和 `curl` 命令中包含敏感文件名的情况

### 🟡 中：localPolicyCache key 冲突修复 (localPolicyCache.ts)

**问题**：`resource_hint` 为 `undefined` 时，所有同类工具共享同一个 key（如 `file_read:*`）。缓存一个 `file_read` 会导致所有无 hint 的 `file_read` 被放行。

**修复**：`undefined` 的 `resource_hint` 映射为空字符串 `""` 而非通配符 `"*"`。key 格式变为 `tool_kind:`（无 hint 时）或 `tool_kind:path`（有 hint 时）。

### 🟡 中：flushWorker 数据丢失风险修复 (flushWorker.ts)

**问题**：flush 失败后，catch 块把内存队列全部 drain 出来写磁盘。如果磁盘写入也失败，所有事件直接丢失。

**修复**：增加嵌套 try-catch——磁盘写入失败时，使用 `requeue()` 将事件放回内存队列。日志级别从 `warn` 提升到 `error` 并记录双重错误原因。

## 测试更新

- `sanitizer.test.ts` 新增 2 个回归测试：
  1. 验证敏感内容在长前缀后仍被正确脱敏
  2. 验证超出预览窗口的敏感内容绝不泄露原文
- 测试总数从 15 增加到 16，全部通过

## 验证结果

```text
✓ TypeScript 类型检查：通过
✓ 单元测试：16/16 通过
✓ 构建 tsc：通过
```

## 修改文件一览

| 文件 | 改动类型 |
|---|---|
| `src/sanitizer/redact.ts` | 修复：脱敏顺序 |
| `src/events/normalizeMessage.ts` | 修复：去除双重截断 |
| `src/events/normalizeToolResult.ts` | 修复：去除双重截断 |
| `src/hooks/messageHooks.ts` | 重构：提取 Hook 注册逻辑 |
| `src/hooks/toolHooks.ts` | 重构：提取 Hook 注册逻辑 |
| `src/index.ts` | 重构：委托给 Hook 模块 |
| `src/utils/id.ts` | 修复：crypto.randomUUID() |
| `src/queue/memoryQueue.ts` | 修复：最大重试次数 |
| `src/policy/fallbackPolicy.ts` | 修复：shell_exec 敏感检测 |
| `src/policy/localPolicyCache.ts` | 修复：缓存 key 冲突 |
| `src/worker/flushWorker.ts` | 修复：磁盘失败时回写内存 |
| `src/tests/sanitizer.test.ts` | 新增：回归测试 |
| `src/tests/integration.test.ts` | 新增：HTTP 集成测试 |
| `src/demo/openclawDemo.ts` | 修复：重写 demo，独立可运行 |
| `doc/round-14-code-review-and-fixes.md` | 新增：本轮记录 |

## 集成测试与端到端验证

本轮之前，所有 15 个测试都是纯单元测试（测函数输入输出），没有任何测试走真实 HTTP 链路。demo 脚本也因为 `index.ts` 缺少 `activate`/`deactivate` 导出而无法运行。

### 新增集成测试 (integration.test.ts)

8 个测试，启动真实 HTTP 服务器（模拟 Mock Core），用 `AuditClient` 发真实 POST 请求：

| 测试 | 验证内容 |
|---|---|
| ALLOW | file_read README.md → Core 返回 ALLOW → mapper 不阻断 |
| BLOCK | shell rm -rf → Core 返回 BLOCK → mapper 输出 blockReason |
| ASK | http_request external URL → Core 返回 ASK → mapper 输出 requireApproval |
| WARN | shell ls → Core 返回 WARN → mapper 输出 warning，不阻断 |
| modified_params | Core 返回改参 → mapper 输出 modifiedParams |
| Core 不可用 + 高危 | fallbackPolicy BLOCK shell_exec |
| Core 不可用 + shell 敏感文件 | fallbackPolicy BLOCK cat .env |
| HTTP 超时 | 不可达地址抛错 → fallbackPolicy 正常执行 |

```text
✓ src/tests/integration.test.ts  (8 tests)
```

### 修复 demo 脚本

重写了 [openclawDemo.ts](openclaw-plugin/src/demo/openclawDemo.ts)：
- 不再依赖不存在的 `activate`/`deactivate`/`pluginRuntime` 导出
- 直接使用 `AuditClient` + `mapAuditDecision` + `evaluateFallbackPolicy`
- 5 个演示场景全部通过，与真实 Mock Core 完成 HTTP 往返

```text
场景 1: 正常读取 README → ALLOW ✅
场景 2: 读取 .env → BLOCK ✅
场景 3: 执行 rm -rf → BLOCK ✅
场景 4: 访问外部 URL → ASK ✅
场景 5: Core 不可用 → 降级 BLOCK ✅
结果: 5 通过 / 0 失败
```

## 验证结果（更新）

```text
✓ TypeScript 类型检查：通过
✓ 单元测试：16/16 通过
✓ 集成测试：8/8 通过（24/24 总计）
✓ 构建 tsc：通过
✓ Demo 演示：5/5 场景通过
```

## 修改文件一览（更新）

## 总结

本轮执行了三件事：

1. **代码审查** — 逐文件通读 27 个源文件，发现 1 个严重 bug、2 个高优问题、4 个中优问题
2. **修复关键缺陷** — 修复了脱敏顺序、死代码、ID 安全、队列健壮性、敏感检测覆盖、缓存冲突、数据丢失风险
3. **补齐集成验证** — 新增 8 个 HTTP 集成测试 + 修复 demo 脚本，让整个链路真的有 HTTP 往返可验证

最关键的是脱敏截断顺序 bug：超过 500 字符的消息中的密码/token/密钥可能未被清洗就直接写入事件载荷。同时补齐了从"所有测试都是纯函数单元测试"到"有真实 HTTP 集成测试 + 可运行 demo 脚本"的验证能力差距。

## 剩余低优先级问题（留待后续轮次）

1. `inferRiskHint` 中 `|delete|unlink|` 子串匹配可能产生误报
2. `summarizeValue` 对大数组先序列化再截断，浪费 CPU
3. `sha256` 对循环引用会抛异常
4. `parseAuditDecision` 不验证 `approval` 子结构
5. `diskQueue.enqueueMany` 串行写入性能较低
6. Logger meta 可能覆盖日志条目字段
7. `Date.now()` 作为降级审批 ID 不唯一
