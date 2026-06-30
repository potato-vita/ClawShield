# TraceShield Core 接入指南

## 启动

```bash
docker compose up -d postgres

cd core
npm install
cp .env.example .env
npm run db:migrate
npm run dev
```

另开终端执行：

```bash
cd core
npm run seed:demo
npm run smoke
```

## OpenClaw 插件

Core 接口与插件现有契约相同，无需改路径：

```bash
cd openclaw-plugin
TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787 npm run demo:openclaw
```

也可使用快捷脚本：

```bash
npm run demo:core
```

## 前端数据映射

| UI 区域 | API |
| --- | --- |
| 顶部运行指标 | `GET /v1/dashboard/runtime-status` |
| 左侧审计时间线 | `GET /v1/audit/events?limit=50` |
| 中间风险图 | `GET /v1/runs/:runId/risk-graph` |
| 右侧决策详情 | `GET /v1/tool-calls/:toolCallId/decision` |
| 底部证据路径 | `GET /v1/runs/:runId/evidence-path` |
| 实时刷新 | `GET /v1/stream/audit-events` |

前端首次加载先请求查询 API，然后连接 SSE。收到 `audit_event` 时刷新 timeline/decision/graph/status；收到 `trace_event` 时按 run 刷新证据和工具结果。

## 开发与隐私

- `mock-core` 仅保留给旧的无数据库演示；新联调使用 `core` 。
- 不要提交 `core/.env`。
- raw 数据保存开关默认必须为 `false`。
- 完整接口格式见 `core/docs/api.md`。

## 高危命令人工确认

- Core 对 `rm -rf`、`mkfs`、`dd if=` 等破坏性 shell 命令返回 `ASK critical`。
- 插件将 `ASK` 映射为 OpenClaw `requireApproval`；默认动作和超时动作均为 `BLOCK`。
- 弹窗或审批消息由 OpenClaw 宿主界面/频道负责展示，TraceShield 不自己绘制 UI。
- 纯 `openclaw agent` 命令没有来源对话或已配置的审批目标时，OpenClaw 会报告 approval route unavailable 并按默认动作拒绝。
- OpenClaw 宿主需启用 `approvals.plugin` 并选择 session 或 targets 路由，才能把确认请求发送到 Control UI/消息频道。
- Eino 可以在后续承担企业级审批编排，但不是本地人工确认的必要依赖。
