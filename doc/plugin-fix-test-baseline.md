# TraceShield 插件修正基线记录

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 记录日期 | 2026-06-17 |
| 当前分支 | `main` |
| 当前 commit | `66457c5a0465ef551822126b6dac965ab2631556` |
| 工作区状态 | 存在用户手动改动，未执行 `git checkout main` / `git pull origin main` 以免覆盖本地修改 |

## 基线命令结果

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `cd openclaw-plugin && npm run typecheck` | 通过 | TypeScript 类型检查通过 |
| `cd openclaw-plugin && npm run test` | 通过 | 6 个测试文件、30 个用例通过；本地 HTTP 集成测试需允许监听 `127.0.0.1` |
| `cd openclaw-plugin && npm run build` | 通过 | `tsc -p tsconfig.json` 构建通过 |
| `cd mock-core && npm run typecheck` | 通过 | Mock Core 类型检查通过 |
| `cd openclaw-plugin && npm run demo:openclaw` | 通过 | 5 个演示场景通过；需要 Mock Core 监听 `127.0.0.1:8787` |

## 本轮新增测试

- `openclaw-plugin/src/tests/config.test.ts`

## 真实 OpenClaw 验证状态

本机 OpenClaw 2026.6.6 已验证插件加载和真实 `before_tool_call` 阻断链路：

- `openclaw plugins inspect traceshield-security-plugin --json` 显示插件 `enabled: true`、`status: loaded`。
- `openclaw agent` 真实调用 `exec` 执行 `rm -rf /tmp/traceshield-codex-check` 时，TraceShield 返回 `BLOCK`。
- Gateway 日志记录 `TraceShield audit decision received`，`matched_rules=["dangerous_rm_rf"]`。
