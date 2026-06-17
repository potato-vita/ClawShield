# TraceShield 插件修正与测试任务书

## 0. 文档目的

本文档用于交给 Codex 执行，对 `https://github.com/potato-vita/TraceShield` 仓库 `main` 分支中的 OpenClaw 插件部分进行一次小范围、可验证、可回滚的修正与测试。

本轮目标不是继续扩大功能，而是把当前插件 MVP 打磨成更可靠的工程状态。

核心原则：

```text
1. 不依赖口头判断，所有结论必须用代码、测试、构建或日志证明。
2. 不重构 Core，不做 Eino，不做数据库，不做风险图。
3. 只修 OpenClaw 插件当前已经实现但还不够稳的部分。
4. 每一步修改后都必须运行测试。
5. 如果实际代码与本文档判断不一致，以仓库代码为准，并在记录中说明差异。
```

如果 Claude Code 或其他工具质疑方案，请不要争论“谁更权威”，直接回到验收标准：

```text
代码能不能编译？
测试能不能通过？
插件入口是否更清晰？
配置是否真的生效？
Mock Core 联调是否可复现？
真实 OpenClaw 接入步骤是否写清楚？
```

## 1. 当前状态理解

根据当前 `main` 分支，项目已经具备一个可演示的 OpenClaw 插件 MVP。

已完成能力大致包括：

```text
1. openclaw-plugin 插件目录已经存在。
2. mock-core 目录已经存在。
3. 插件 manifest 已存在：openclaw-plugin/openclaw.plugin.json。
4. 插件入口已注册 traceshield_status 工具。
5. 插件入口已注册 message 类 hook。
6. 插件入口已注册 before_tool_call 和 after_tool_call。
7. before_tool_call 会调用 AuditClient 请求 /v1/audit/tool-call。
8. Mock Core 会根据 rm -rf、.env、id_rsa、外部 URL 等规则返回模拟决策。
9. AuditDecision 已经能映射成 ALLOW / WARN / ASK / BLOCK / modified_params。
10. 已有脱敏模块。
11. 已有 fallback policy。
12. 已有测试报告，记录 typecheck、test、build 通过。
```

但当前状态仍然有几个工程问题：

```text
1. src/index.ts 承担太多职责，后续维护困难。
2. 部分源码在 GitHub raw 中显示为超长单行，可读性较差。
3. openclaw.plugin.json 中声明的部分配置项，config.ts 未完整读取。
4. README 说支持一些配置，但需要用测试证明配置真的生效。
5. demo 是模拟 HookRegistry，并不能替代真实 OpenClaw 加载验证。
6. 缺少一份真实接入 OpenClaw 的操作记录模板。
```

本轮只修这些问题。

## 2. 本轮禁止做的事情

Codex 本轮不要做以下事情：

```text
1. 不要重写整个插件。
2. 不要替换 OpenClaw SDK。
3. 不要把 mock-core 改成真实 Core。
4. 不要新增数据库。
5. 不要新增 Eino 前端。
6. 不要引入大型框架。
7. 不要修改项目名称。
8. 不要删除已有测试。
9. 不要为了格式化制造大面积无意义逻辑变更。
10. 不要把敏感信息写入测试样例或日志。
```

允许做：

```text
1. 小范围拆分 index.ts。
2. 补齐配置读取。
3. 补充配置测试。
4. 补充真实 OpenClaw 接入文档。
5. 格式化源码，使代码可读。
6. 修复因拆分或配置补齐导致的类型错误。
```

## 3. 执行前基线检查

Codex 首先执行以下步骤。

### 3.1 拉取 main 分支

```bash
git checkout main
git pull origin main
```

如果当前工作区有未提交修改，先停止并报告，不要覆盖。

### 3.2 查看目录结构

```bash
find . -maxdepth 3 -type f | sort
```

重点确认存在：

```text
openclaw-plugin/package.json
openclaw-plugin/openclaw.plugin.json
openclaw-plugin/src/index.ts
mock-core/package.json
mock-core/server.ts
README.md
```

### 3.3 运行基线验证

在 `openclaw-plugin/` 下运行：

```bash
npm install
npm run typecheck
npm run test
npm run build
```

在 `mock-core/` 下运行：

```bash
npm install
npm run typecheck
```

如果基线失败，先不要做重构，先记录失败命令和错误信息，然后修最小问题使基线恢复。

### 3.4 生成基线记录

新增或更新：

```text
doc/plugin-fix-test-baseline.md
```

内容包括：

```text
1. 当前分支。
2. 当前 commit hash。
3. npm run typecheck 是否通过。
4. npm run test 是否通过。
5. npm run build 是否通过。
6. mock-core typecheck 是否通过。
7. 如果失败，记录失败原因。
```

## 4. 修正任务一：整理源码格式

### 4.1 目标

让 TypeScript 源码从超长单行变成正常可读格式。

### 4.2 要求

优先使用项目已有格式工具。如果没有格式工具，可以新增 Prettier，但必须保持改动可控。

建议新增：

```text
openclaw-plugin/.prettierrc
openclaw-plugin/.prettierignore
```

建议 `.prettierrc`：

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100
}
```

建议 `.prettierignore`：

```text
dist
node_modules
coverage
.traceshield
```

在 `openclaw-plugin/package.json` 中增加：

```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.ts\" \"docs/**/*.md\"",
    "format:check": "prettier --check \"src/**/*.ts\" \"docs/**/*.md\""
  }
}
```

如果不想格式化 docs，也可以只格式化 `src/**/*.ts`。

### 4.3 注意事项

```text
1. 格式化不应改变业务逻辑。
2. 格式化后必须运行 typecheck 和 test。
3. 如果格式化导致 diff 太大，要说明这是纯格式化。
```

### 4.4 验收标准

```text
1. src/index.ts 和关键模块不再是超长单行。
2. npm run format:check 通过。
3. npm run typecheck 通过。
4. npm run test 通过。
```

## 5. 修正任务二：拆分 src/index.ts

### 5.1 目标

降低 `src/index.ts` 的复杂度，让插件注册逻辑更清楚。

### 5.2 建议新增目录

```text
openclaw-plugin/src/register/
  registerStatusTool.ts
  registerFlushWorker.ts
  registerMessageHooks.ts
  registerToolHooks.ts
  registerSecurityMiddleware.ts
```

### 5.3 拆分原则

`src/index.ts` 只保留：

```text
1. definePluginEntry。
2. loadConfig。
3. createLogger。
4. 初始化共享 queue。
5. 调用各 registerXxx 函数。
6. export default pluginEntry。
```

不要把所有逻辑继续堆在 `index.ts`。

### 5.4 每个模块职责

#### registerStatusTool.ts

负责注册：

```text
traceshield_status
```

输出内容至少包括：

```text
1. 插件已加载。
2. Core URL。
3. Audit timeout。
4. fallback 是否开启。
5. debug_full_payload 是否开启。
6. 当前队列长度。
```

#### registerFlushWorker.ts

负责注册：

```text
traceshield-event-flush-worker
```

包括：

```text
1. 创建 DiskQueue。
2. 创建 EventClient。
3. 创建 FlushWorker。
4. start。
5. stop。
```

#### registerMessageHooks.ts

负责注册：

```text
message_received
llm_input
llm_output
message_sending
agent_end
```

这些事件只进入异步队列，不阻断。

#### registerToolHooks.ts

负责注册：

```text
before_tool_call
after_tool_call
```

其中 `before_tool_call` 负责：

```text
1. normalizeToolCall。
2. buildAuditRequest。
3. 调用 auditClient.auditToolCall。
4. 成功后 mapAuditDecision。
5. 失败后 evaluateFallbackPolicy。
6. 返回 OpenClaw 可识别结果。
```

#### registerSecurityMiddleware.ts

负责注册：

```text
before_prompt_build
agentToolResultMiddleware
registerSecurityAuditCollector
```

### 5.5 不要改变的行为

拆分后，以下行为必须保持不变：

```text
1. traceshield_status 仍可注册。
2. message 类 hook 仍可注册。
3. before_tool_call 仍会同步审计。
4. after_tool_call 仍会记录工具结果。
5. Core 请求失败时仍会 fallback。
6. BLOCK 仍返回 block: true。
7. ASK 仍返回 requireApproval。
```

### 5.6 验收标准

```text
1. src/index.ts 明显变短。
2. register 目录职责清晰。
3. npm run typecheck 通过。
4. npm run test 通过。
5. npm run build 通过。
6. npm run demo:openclaw 能运行。
```

## 6. 修正任务三：补齐配置加载

### 6.1 目标

让 `openclaw.plugin.json` 中声明的主要配置项都能被 `loadConfig` 正确读取。

当前重点补齐：

```text
event_flush_timeout_ms
event_flush_interval_ms
disk_queue_dir
memory_queue_max_events
local_allow_tool_kinds
high_risk_tool_kinds
```

### 6.2 环境变量建议

为以下配置增加环境变量读取：

```text
TRACESHIELD_EVENT_FLUSH_TIMEOUT_MS
TRACESHIELD_EVENT_FLUSH_INTERVAL_MS
TRACESHIELD_DISK_QUEUE_DIR
TRACESHIELD_MEMORY_QUEUE_MAX_EVENTS
TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS
TRACESHIELD_HIGH_RISK_TOOL_KINDS
```

其中列表类配置可以用英文逗号分隔：

```text
TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS=file_read,read_only
TRACESHIELD_HIGH_RISK_TOOL_KINDS=shell_exec,file_write,file_delete,network_request
```

### 6.3 配置读取规则

优先级：

```text
1. OpenClaw plugin config source
2. 环境变量
3. defaultPluginConfig
```

非法配置处理：

```text
1. 数字配置非数字时回退默认值。
2. 布尔配置只接受 true / false。
3. mode 只接受 development / demo / production。
4. 数组配置为空时回退默认值。
5. production 模式下 debug_full_payload 不应默认开启。
```

### 6.4 manifest 同步

检查 `openclaw.plugin.json` 的 `configSchema` 是否包含上述配置。

如果缺少，补齐：

```text
memory_queue_max_events
local_allow_tool_kinds
high_risk_tool_kinds
```

数组配置 schema 可使用：

```json
{
  "type": "array",
  "items": {
    "type": "string"
  }
}
```

如果 OpenClaw manifest 对数组配置支持有限，则可以用 string，并在代码中 split。

### 6.5 验收标准

```text
1. loadConfig 能读取所有主要配置项。
2. manifest 中声明的配置和代码读取逻辑一致。
3. 环境变量能覆盖默认值。
4. 非法配置不会导致插件崩溃。
5. npm run typecheck 通过。
6. npm run test 通过。
```

## 7. 修正任务四：补充配置测试

### 7.1 目标

用测试证明配置读取真的工作，而不是只在 README 里写了。

### 7.2 建议新增测试文件

```text
openclaw-plugin/src/tests/config.test.ts
```

### 7.3 测试用例

至少覆盖：

```text
1. 默认配置加载。
2. source 中的 core_base_url 覆盖默认值。
3. source 中的 audit_timeout_ms 覆盖默认值。
4. source 中的 event_flush_timeout_ms 覆盖默认值。
5. source 中的 event_flush_interval_ms 覆盖默认值。
6. source 中的 disk_queue_dir 覆盖默认值。
7. source 中的 memory_queue_max_events 覆盖默认值。
8. local_allow_tool_kinds 能读取数组或逗号字符串。
9. high_risk_tool_kinds 能读取数组或逗号字符串。
10. 非法 mode 回退默认值。
11. 非法数字回退默认值。
12. debug_full_payload 默认 false。
```

### 7.4 验收标准

```text
1. 新增 config.test.ts。
2. npm run test 通过。
3. 测试数量增加。
4. 测试中不包含真实 token、真实密码、真实私钥。
```

## 8. 修正任务五：真实 OpenClaw 接入验证文档

### 8.1 目标

补一份真实环境接入文档。即使当前机器没有 OpenClaw 环境，也要给出可执行步骤和记录模板。

新增：

```text
doc/real-openclaw-integration.md
```

### 8.2 文档结构

文档必须包含：

```text
1. 验证目的
2. 验证环境
3. 启动 Mock Core
4. 构建插件
5. 配置 OpenClaw 加载插件
6. 调用 traceshield_status
7. 正常工具调用测试
8. .env 阻断测试
9. rm -rf 阻断测试
10. 外部 URL 审批测试
11. Core 关闭后的 fallback 测试
12. 结果记录表
13. 常见失败原因
```

### 8.3 推荐命令

Mock Core：

```bash
cd mock-core
npm install
npm run dev
```

插件构建：

```bash
cd openclaw-plugin
npm install
npm run build
```

插件本地演示：

```bash
cd openclaw-plugin
npm run demo:openclaw
```

真实 OpenClaw 加载部分，如果无法确定用户本地命令，不要瞎写绝对命令。可以写成：

```text
根据 OpenClaw 当前插件安装方式，将 openclaw-plugin/openclaw.plugin.json 指向 dist/index.js。
确认插件出现在 openclaw plugins list 或对应插件列表中。
```

### 8.4 结果记录表

文档中必须包含表格：

```text
| 测试项 | 输入 | 预期结果 | 实际结果 | 是否通过 | 证据 |
| --- | --- | --- | --- | --- | --- |
| traceshield_status | 调用状态工具 | 返回 Core URL 和队列状态 |  |  |  |
| 正常读取 README | file_read README.md | ALLOW |  |  |  |
| 读取 .env | file_read .env | BLOCK |  |  |  |
| 删除命令 | shell_exec rm -rf | BLOCK |  |  |  |
| 外部 URL | network_request example.com | ASK |  |  |  |
| Core 关闭后高危命令 | shell_exec rm -rf | fallback BLOCK |  |  |  |
```

### 8.5 验收标准

```text
1. doc/real-openclaw-integration.md 存在。
2. 文档不声称已经完成真实验证，除非真的跑过。
3. 文档给出可执行步骤。
4. 文档给出结果记录表。
5. 文档能区分 demo 验证和真实 OpenClaw 验证。
```

## 9. 修正任务六：更新 README 和测试报告

### 9.1 README 更新

README 只做小改。

更新内容：

```text
1. 当前状态改成：插件 MVP 已完成，真实 OpenClaw 接入验证待记录。
2. 增加 npm run format / format:check。
3. 增加 real-openclaw-integration.md 链接。
4. 明确 demo:openclaw 是模拟 HookRegistry 演示，不等于真实 OpenClaw 验证。
```

### 9.2 测试报告更新

更新：

```text
openclaw-plugin/docs/plugin-test-report.md
```

记录：

```text
1. 本次执行日期。
2. typecheck 结果。
3. test 结果。
4. build 结果。
5. format:check 结果。
6. mock-core typecheck 结果。
7. 新增测试文件名称。
8. 仍未完成的真实接入验证。
```

### 9.3 验收标准

```text
1. README 不夸大当前状态。
2. 测试报告与实际命令结果一致。
3. demo 和真实接入验证被明确区分。
```

## 10. 最终测试清单

所有修改完成后，必须运行：

### 10.1 openclaw-plugin

```bash
cd openclaw-plugin
npm run format:check
npm run typecheck
npm run test
npm run build
npm run demo:openclaw
```

### 10.2 mock-core

```bash
cd mock-core
npm run typecheck
```

如果要验证 Mock Core 运行：

```bash
cd mock-core
npm run dev
```

然后另开终端执行：

```bash
curl -s -X POST http://127.0.0.1:8787/v1/audit/tool-call \
  -H "content-type: application/json" \
  -d '{"tool_name":"shell","tool_kind":"shell_exec","raw_params":{"cmd":"rm -rf /tmp/demo"},"risk_hint":"shell_exec"}'
```

预期返回包含：

```json
{
  "decision": "BLOCK"
}
```

注意：如果 Windows PowerShell 不支持上述 curl 写法，需要改成 PowerShell 的 `Invoke-RestMethod`，但不要改变接口语义。

## 11. 最终交付物

本轮完成后，Codex 应该提交以下内容：

```text
1. 格式化后的 TypeScript 源码。
2. 拆分后的 src/register/*.ts。
3. 补齐后的 config.ts。
4. 新增或更新的 config.test.ts。
5. 新增 doc/plugin-fix-test-baseline.md。
6. 新增 doc/real-openclaw-integration.md。
7. 更新 README.md。
8. 更新 openclaw-plugin/docs/plugin-test-report.md。
```

如果某项无法完成，必须在最终回复中说明：

```text
1. 哪项没完成。
2. 为什么没完成。
3. 当前是否影响插件演示。
4. 下一步如何补。
```

## 12. 给 Codex 的完整执行指令

可以直接复制下面这段给 Codex：

```text
请在 https://github.com/potato-vita/TraceShield 仓库 main 分支上执行一次小范围插件修正和测试。

本轮只处理 openclaw-plugin 和 mock-core，不做 Core、Eino、数据库、风险图。

请严格按以下目标完成：

1. 先拉取 main，确认没有未提交修改。
2. 运行 openclaw-plugin 的 npm install、typecheck、test、build，运行 mock-core 的 npm install、typecheck，记录基线到 doc/plugin-fix-test-baseline.md。
3. 给 openclaw-plugin 增加格式化能力，必要时添加 Prettier，让 src/**/*.ts 变成可读格式，并增加 format 和 format:check 脚本。
4. 拆分 src/index.ts，把状态工具、flush worker、消息 hook、工具 hook、安全中间件分别放入 src/register/*.ts，保持原有行为不变。
5. 补齐 config.ts，让它能读取 event_flush_timeout_ms、event_flush_interval_ms、disk_queue_dir、memory_queue_max_events、local_allow_tool_kinds、high_risk_tool_kinds，并支持对应环境变量。
6. 检查 openclaw.plugin.json 的 configSchema，使 manifest 声明与代码读取逻辑一致。
7. 新增 config.test.ts，覆盖默认配置、source 覆盖、环境变量覆盖、非法配置回退、数组配置读取、debug_full_payload 默认关闭。
8. 新增 doc/real-openclaw-integration.md，写清真实 OpenClaw 加载验证步骤和结果记录表。注意 demo:openclaw 是模拟 HookRegistry，不等于真实 OpenClaw 验证。
9. 更新 README.md，说明当前是插件 MVP，真实 OpenClaw 接入验证待记录，不要夸大状态。
10. 更新 openclaw-plugin/docs/plugin-test-report.md，记录本次 format:check、typecheck、test、build、mock-core typecheck 的真实结果。
11. 最终必须运行：
    - cd openclaw-plugin && npm run format:check
    - cd openclaw-plugin && npm run typecheck
    - cd openclaw-plugin && npm run test
    - cd openclaw-plugin && npm run build
    - cd openclaw-plugin && npm run demo:openclaw
    - cd mock-core && npm run typecheck

约束：
- 不要重写整个插件。
- 不要删除已有测试。
- 不要实现真实 Core。
- 不要新增数据库。
- 不要做 Eino。
- 不要把敏感信息写入日志或测试。
- 如果实际代码与任务书判断不一致，以代码为准，并在最终报告说明差异。

最终回复请按以下格式：

一、修改摘要
二、测试结果
三、仍未完成或需要人工验证的事项
四、下一步建议
```

## 13. 判断完成的标准

这轮不是看“写了多少代码”，而是看下面这些是否成立：

```text
1. 插件代码更可读。
2. 配置声明和配置读取一致。
3. 配置行为有测试证明。
4. demo 仍然能跑。
5. typecheck / test / build 全部通过。
6. README 不夸大。
7. 真实 OpenClaw 接入有明确验证文档。
```

如果这些都成立，本轮修正就算完成。

