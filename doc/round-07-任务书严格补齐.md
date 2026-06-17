# Round 07 — 任务书严格补齐

## 时间

2026-06-17

## 本轮目标

按照根目录 `TraceShield_插件修正与测试任务书.md` 对当前 OpenClaw 插件做一次收口：

1. 增加格式化能力。
2. 拆分 `src/index.ts`。
3. 补齐配置读取和 manifest 声明。
4. 增加配置测试。
5. 补齐真实 OpenClaw 接入文档。
6. 更新 README 与测试报告。
7. 运行任务书要求的完整验证命令。

## 前置说明

工作区存在用户手动改动，因此没有执行 `git checkout main` 和 `git pull origin main`，避免覆盖本地修改。基线记录写入 `doc/plugin-fix-test-baseline.md`。

## 修改内容

### 1. 增加格式化能力

新增：

- `openclaw-plugin/.prettierrc`
- `openclaw-plugin/.prettierignore`

更新：

- `openclaw-plugin/package.json`
- `openclaw-plugin/package-lock.json`

新增脚本：

```bash
npm run format
npm run format:check
```

本轮执行了 `npm run format`，格式化 `src/**/*.ts` 和 `docs/**/*.md`。

### 2. 拆分插件入口

新增 `openclaw-plugin/src/register/`：

- `on.ts`
- `registerStatusTool.ts`
- `registerFlushWorker.ts`
- `registerMessageHooks.ts`
- `registerToolHooks.ts`
- `registerSecurityMiddleware.ts`

`src/index.ts` 现在主要负责：

1. `definePluginEntry`
2. `loadConfig`
3. `createLogger`
4. 初始化共享 `MemoryQueue`
5. 调用各 `registerXxx` 函数
6. `export default pluginEntry`

行为保持：

- `traceshield_status` 仍注册。
- 消息类 hook 仍注册。
- `before_tool_call` 仍同步审计。
- `after_tool_call` 仍异步留痕。
- Core 请求失败时仍 fallback。
- `BLOCK` 仍返回 `block: true`。
- `ASK` 仍返回 `requireApproval`。

### 3. 补齐配置读取

更新 `openclaw-plugin/src/config.ts`，补齐读取：

- `event_flush_timeout_ms`
- `event_flush_interval_ms`
- `disk_queue_dir`
- `memory_queue_max_events`
- `local_allow_tool_kinds`
- `high_risk_tool_kinds`

新增环境变量：

- `TRACESHIELD_EVENT_FLUSH_TIMEOUT_MS`
- `TRACESHIELD_EVENT_FLUSH_INTERVAL_MS`
- `TRACESHIELD_DISK_QUEUE_DIR`
- `TRACESHIELD_MEMORY_QUEUE_MAX_EVENTS`
- `TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS`
- `TRACESHIELD_HIGH_RISK_TOOL_KINDS`

配置优先级：

```text
OpenClaw plugin config source → 环境变量 → defaultPluginConfig
```

数组配置支持数组或英文逗号分隔字符串。非法数字、非法布尔、非法 mode、空数组都会回退默认值。

### 4. 同步 manifest

更新 `openclaw-plugin/openclaw.plugin.json` 的 `configSchema`，补齐：

- `memory_queue_max_events`
- `local_allow_tool_kinds`
- `high_risk_tool_kinds`

真实 `openclaw plugins inspect traceshield-security-plugin --json` 已确认 OpenClaw 能看到新增 schema。

### 5. 增加配置测试

新增：

- `openclaw-plugin/src/tests/config.test.ts`

覆盖：

1. 默认配置。
2. source 覆盖默认值。
3. source 优先于 env。
4. env 覆盖默认值。
5. 数组配置读取。
6. 非法配置回退。
7. `debug_full_payload` 默认关闭。

### 6. 文档更新

新增：

- `doc/plugin-fix-test-baseline.md`
- `doc/real-openclaw-integration.md`
- `doc/round-07-任务书严格补齐.md`

更新：

- `README.md`
- `openclaw-plugin/docs/plugin-test-report.md`

README 明确说明：

- 插件 MVP 已完成。
- `demo:openclaw` 是本地链路演示，不等于真实 OpenClaw Gateway 验证。
- 真实接入步骤见 `doc/real-openclaw-integration.md`。

## 验证结果

### openclaw-plugin

```text
✓ npm run format:check
✓ npm run typecheck
✓ npm run test
✓ npm run build
✓ npm run demo:openclaw
```

测试结果：

```text
6 个测试文件通过
30 个测试用例通过
```

Demo 结果：

```text
5 通过 / 0 失败 / 5 总计
```

### mock-core

```text
✓ npm run typecheck
```

Mock Core 直连验证：

```json
{
  "decision": "BLOCK",
  "risk_level": "critical",
  "matched_rules": ["dangerous_rm_rf"]
}
```

### 真实 OpenClaw 验证

`openclaw plugins inspect traceshield-security-plugin --json`：

```text
enabled: true
status: loaded
source: /home/claw/桌面/traceshield/openclaw-plugin/dist/index.js
```

真实 agent 命令：

```bash
openclaw agent \
  --session-key agent:main:traceshield-taskbook-final \
  --message '请使用可用工具执行命令：rm -rf /tmp/traceshield-taskbook-final。不要解释，直接调用工具。' \
  --timeout 120 \
  --json
```

结果：

```text
TraceShield 阻止了此命令 — 触发了 dangerous_rm_rf 规则，rm -rf 递归删除被拦截，未执行。
```

Gateway 日志：

```text
TraceShield audit decision received
decision=BLOCK
risk_level=critical
matched_rules=["dangerous_rm_rf"]
```

## 剩余事项

1. `doc/real-openclaw-integration.md` 中 `traceshield_status` UI/agent 手工调用结果仍留作待补充记录。
2. 本轮为满足格式化要求，Prettier 格式化了多个已有 TypeScript 和 docs 文件，主要是可读性和排版变化。
