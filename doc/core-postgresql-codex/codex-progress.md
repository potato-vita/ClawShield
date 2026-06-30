# TraceShield Core + PostgreSQL Codex 执行记录

> 记录目录按用户要求设为 `doc/core-postgresql-codex/`；后续 Round 1-8 将继续追加到本文件，不覆盖已有记录。

## Round 0 - Repository Check

### Goal

- 检查 TraceShield 仓库结构、当前分支和本地 Node.js/npm 环境。
- 确认 `openclaw-plugin` 和 `mock-core` 的项目文件存在。
- 只创建执行记录，不修改业务代码。

### Repository Snapshot

- 当前分支：`main`
- Node.js：`v24.14.1`
- npm：`11.11.0`
- `openclaw-plugin/package.json`：存在
- `mock-core/package.json`：存在
- 原 `doc/` 目录：存在
- 原 `docs/` 目录：不存在

### Main Directories

```text
.
├── .traceshield/
├── core/
├── doc/
│   └── core-postgresql-codex/
├── mock-core/
└── openclaw-plugin/
```

### Files Added

- `doc/core-postgresql-codex/codex-progress.md`

### Files Changed

- 无。

### Commands Run

```bash
find . -maxdepth 2 -mindepth 1 ... | sort
git branch --show-current
node -v
npm -v
ls -la
test -f openclaw-plugin/package.json
test -f mock-core/package.json || echo "mock-core package may not exist"
test -d doc
test -d docs
```

### Result

- Success。仓库结构和必要项目文件已确认。
- Round 0 未改动任何业务代码。
- 开始执行前，根目录执行方案文件本身为未跟踪文件；本轮不对其做任何改动。

### Verification

- [x] 当前分支已记录
- [x] 主要目录已记录
- [x] Node.js 和 npm 版本已记录
- [x] `openclaw-plugin/package.json` 存在
- [x] `mock-core/package.json` 存在
- [x] 独立记录目录与记录文件已创建
- [x] 无业务代码改动

### Notes

- 执行方案原建议路径为 `docs/codex-progress.md`。本次按用户明确要求，改用 `doc/core-postgresql-codex/codex-progress.md`。
- 仓库已有 `core/` 目录；Round 1 开始前应先检查其现有内容，避免覆盖用户已有工作。

### Next Round

- Round 1：PostgreSQL 部署与数据库 Schema。

## Round 1 - PostgreSQL Deployment and Schema

### Goal

- 提供 PostgreSQL 16 Compose 部署、Core TypeScript 项目基础和 11 张核心表。
- 提供可重复执行的迁移、策略种子与数据库检查脚本。

### Files Added

- `docker-compose.yml`
- `core/package.json`
- `core/package-lock.json`
- `core/tsconfig.json`
- `core/.env.example`
- `core/src/db/schema.sql`
- `core/src/db/seed_policies.sql`
- `core/src/db/migrate.ts`
- `core/src/db/check.ts`

### Files Changed

- `.gitignore`：忽略 `.env` 与 `core/.env`。

### Commands Run

```bash
docker --version
npm install
apt download postgresql-16 postgresql-client-16 postgresql-client-common libpq5 libllvm17t64
initdb -D /tmp/traceshield-pgdata -U traceshield --auth=trust --encoding=UTF8 --no-locale
pg_ctl -D /tmp/traceshield-pgdata ... start
createdb -h 127.0.0.1 -p 5432 -U traceshield traceshield
cp .env.example .env
npm run db:migrate
npm run db:check
```

### Result

- Success。`db:migrate` 和 `db:check` 均成功。
- PostgreSQL 实测版本：`16.14`。
- 核心表：`11/11`。
- 种子策略：`4`。
- `docker compose up -d postgres` 未能在当前机器执行，原因是系统未安装 Docker，且当前用户无免密 sudo。为完成真实验收，已在 `/tmp` 解包 Ubuntu 官方 PostgreSQL 16 包并启动临时实例；该替代方式未修改系统服务或仓库配置。

### Verification

- [x] Compose 定义 PostgreSQL 16 和 healthcheck
- [x] `CREATE EXTENSION IF NOT EXISTS pgcrypto`
- [x] 11 张核心表存在
- [x] 基础索引和 check 约束已创建
- [x] 4 条策略已 seed
- [x] `db:migrate` 真实成功
- [x] `db:check` 真实成功
- [x] raw payload/params/result 默认关闭

### Next Round

- Round 2：Core 服务骨架与健康检查。

## Round 2 - Core Server and Health Checks

### Goal

- 启动 Fastify Core，读取环境配置并连接 PostgreSQL。
- 提供健康检查和基于数据库的运行状态统计。

### Files Added

- `core/src/server.ts`
- `core/src/config.ts`
- `core/src/db/pool.ts`
- `core/src/routes/health.ts`
- `core/src/routes/dashboard.ts`
- `core/src/types/pluginContract.ts`
- `core/src/types/db.ts`

### Files Changed

- 无。

### Commands Run

```bash
npm run typecheck
npm run build
npm run dev
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/v1/health
curl http://127.0.0.1:8787/v1/dashboard/runtime-status
```

### Result

- Success。Core 已在 `127.0.0.1:8787` 启动。
- `/health` 和 `/v1/health` 返回 `ok=true`、`db_connected=true`。
- 初始 runtime status 四项真实聚合值均为 `0`。
- 验收前端口被旧 `mock-core` 开发进程占用；已仅停止该进程，未修改或删除 `mock-core` 文件。

### Verification

- [x] TypeScript typecheck
- [x] TypeScript build
- [x] Core 默认端口启动
- [x] 根健康检查
- [x] v1 健康检查
- [x] runtime status 合法 JSON 与真实数据库聚合

### Next Round

- Round 3：`POST /v1/audit/tool-call` 与策略决策入库。

## Round 3 - Audit Tool Call and Policy Decisions

### Goal

- 实现与插件契约一致的同步审计接口。
- 实现五类基础策略决策与事务性审计/证据入库。

### Files Added

- `core/src/routes/audit.ts`
- `core/src/services/auditService.ts`
- `core/src/services/policyEngine.ts`
- `core/src/services/evidenceService.ts`
- `core/scripts/audit_curl_examples.sh`

### Files Changed

- `core/src/server.ts`：注册审计路由。

### Commands Run

```bash
npm run typecheck
npm run build
npm run dev
./scripts/audit_curl_examples.sh
psql <database-url> -c "SELECT ... FROM tool_calls/audit_decisions/audit_rule_hits/evidence..."
```

### Result

- Success。五个真实 HTTP 场景结果分别为 `ALLOW / BLOCK / BLOCK / ASK / WARN`。
- 数据库记录：5 tool calls、5 decisions、5 rule hits、5 evidence items、15 evidence steps。
- `saved_raw_params=0`，默认未保存原始参数。
- 首次 SQL 核查命令因 shell 未自动读取 `.env` 而连到不存在的默认 socket；改为明确 PostgreSQL URL 后成功，入库本身未失败。

### Verification

- [x] TypeScript typecheck/build
- [x] 正常 README 读取返回 ALLOW
- [x] `.env` 读取返回 BLOCK
- [x] `rm -rf` 返回 BLOCK
- [x] 外部 URL 返回 ASK 并带 approval
- [x] unknown tool 返回 WARN
- [x] decision/rule/evidence 真实入库
- [x] run 聚合字段在同一事务内刷新
- [x] raw params 默认不持久化

### Next Round

- Round 4：`POST /v1/events/batch` 异步事件入库。

## Round 4 - Batch Event Ingest

### Goal

- 实现批量 TraceEvent 上报、`event_id` 幂等和结构化事件提取。
- 确保 raw payload/result 仅在显式 debug 开关开启时持久化。

### Files Added

- `core/src/routes/events.ts`
- `core/src/services/eventIngestService.ts`

### Files Changed

- `core/src/server.ts`：注册事件路由。

### Commands Run

```bash
npm run typecheck
npm run build
npm run dev
curl -X POST http://127.0.0.1:8787/v1/events/batch ...
psql <database-url> -c "SELECT ... FROM trace_events/messages/tool_results/tool_calls"
```

### Result

- Success。message 首次上报 `inserted=1, message_extracted=1`。
- 同一 `event_id` 重复上报 `inserted=0, duplicated=1`。
- after-tool 上报 `inserted=1, tool_result_extracted=1`。
- 数据库核查：2 events、1 message、1 tool result；缺失的 tool call 已创建 `unknown` 占位。
- `raw_payloads=0`、`raw_results=0`。

### Verification

- [x] TypeScript typecheck/build
- [x] event_id 幂等
- [x] message 提取
- [x] after_tool_call 结果提取
- [x] 缺失 tool call 占位补齐
- [x] session last_seen 更新
- [x] raw payload/result 默认不持久化

### Next Round

- Round 5：前端查询 API、证据路径与风险图。

## Round 5 - Frontend Query APIs

### Goal

- 提供前端时间线、决策详情、证据路径和风险图所需的只读 API。
- 风险图查询时动态生成，不增加图持久化表。

### Files Added

- `core/src/routes/queries.ts`
- `core/src/services/riskGraphService.ts`

### Files Changed

- `core/src/server.ts`：注册查询路由。

### Commands Run

```bash
npm run typecheck
npm run build
npm run dev
curl http://127.0.0.1:8787/v1/dashboard/runtime-status
curl http://127.0.0.1:8787/v1/audit/events?limit=50
curl http://127.0.0.1:8787/v1/tool-calls/<tool_call_id>
curl http://127.0.0.1:8787/v1/tool-calls/<tool_call_id>/decision
curl http://127.0.0.1:8787/v1/runs/<run_id>/evidence-path
curl http://127.0.0.1:8787/v1/runs/<run_id>/risk-graph
```

### Result

- Success。时间线返回 6 条工具调用。
- 决策详情返回 WARN 及 `warn_unknown_tool` 规则命中。
- 证据路径返回 15 steps。
- 风险图返回 6 nodes / 5 edges，包含 `ALLOW/BLOCK/BLOCK/ASK/WARN`。
- runtime status 返回真实聚合：6 calls、2 blocked、2 high-risk、5 policy hits。

### Verification

- [x] TypeScript typecheck/build
- [x] runtime status 真实聚合
- [x] audit timeline
- [x] tool call detail
- [x] decision + rule hits
- [x] evidence path
- [x] dynamic risk graph nodes/edges
- [x] 风险图未落库

### Next Round

- Round 6：与 `openclaw-plugin` 真实 Core 联调。

## Round 6 - OpenClaw Plugin Integration

### Goal

- 使用插件现有 AuditClient/EventClient 与真实 Core 联调。
- 保持接口路径和返回契约不变，确保插件原有测试不回归。

### Files Added

- 无。

### Files Changed

- `openclaw-plugin/package.json`：增加 `demo:core` 快捷命令。
- `openclaw-plugin/src/demo/openclawDemo.ts`：支持通过 EventClient 上报两类异步事件，并将提示文案从 Mock Core 改为通用 Core。

### Commands Run

```bash
cd openclaw-plugin && npm run typecheck
cd openclaw-plugin && npm run test
cd openclaw-plugin && npm run build
cd openclaw-plugin && TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787 npm run demo:openclaw
cd core && npm run db:check
psql <database-url> -c "SELECT ... plugin tool calls/decisions/trace events"
```

### Result

- Success。插件 6 个演示场景全部通过，包括 ALLOW/BLOCK/BLOCK/ASK、本地 fallback BLOCK 和异步事件上报。
- 插件测试：6 files / 30 tests 全部通过。
- 数据库中 `demo-session` 有 5 tool calls（含 1 个结果事件占位）、4 decisions；插件 ID 对应 2 trace events。
- `db:check` 仍为 11/11 tables、4 policies。

### Verification

- [x] 无需修改插件接口路径
- [x] 插件 typecheck/build
- [x] 插件原有 30 tests
- [x] 真实 Core 四类决策
- [x] AuditClient 解析 Core 返回
- [x] EventClient 上报入库
- [x] 数据库有插件产生的 tool calls/decisions/trace events

### Next Round

- Round 7：SSE 实时审计事件流。

## Round 7 - SSE Audit Event Stream

### Goal

- 提供 `GET /v1/stream/audit-events` 长连接。
- 在同步审计和异步事件成功后分别广播 `audit_event` 与 `trace_event`。

### Files Added

- `core/src/routes/stream.ts`
- `core/src/services/streamService.ts`

### Files Changed

- `core/src/routes/audit.ts`：成功决策后广播审计事件。
- `core/src/routes/events.ts`：仅对新插入事件广播跟踪事件。
- `core/src/server.ts`：注册 SSE 路由。

### Commands Run

```bash
npm run typecheck
npm run build
npm run dev
curl -N http://127.0.0.1:8787/v1/stream/audit-events
curl -X POST http://127.0.0.1:8787/v1/audit/tool-call ...
curl -X POST http://127.0.0.1:8787/v1/events/batch ...
```

### Result

- Success。SSE 连接首先收到 `connected`，然后收到 heartbeat、`audit_event` 和 `trace_event`。
- 广播数据仅包含必要标识、决策和风险元数据，不包含 raw params/payload。
- 首个 SSE 测试使用了 10 秒外部 timeout，由于命令编排间隔超时，连接在触发请求前退出；改为持续连接后两类事件均实时收到。

### Verification

- [x] TypeScript typecheck/build
- [x] SSE connected event
- [x] heartbeat
- [x] audit_event 广播
- [x] trace_event 广播
- [x] 连接关闭清理客户端和定时器
- [x] 不影响原有 HTTP API

### Next Round

- Round 8：文档、演示数据、冒烟测试和最终验收。

## Round 8 - Documentation, Demo Data, and Final Acceptance

### Goal

- 完成 Core API/数据库/接入文档。
- 提供可重复的前端演示数据和一键冒烟验收。
- 对 Core、PostgreSQL 和插件执行最终回归。

### Files Added

- `core/docs/api.md`
- `core/scripts/seed_demo_data.ts`
- `core/scripts/smoke_test.ts`
- `core/src/services/statsService.ts`
- `doc/core-postgresql-codex/core-db-design.md`
- `doc/core-postgresql-codex/core-api-usage.md`

### Files Changed

- `core/src/routes/dashboard.ts`：将统计查询分离到 stats service。
- `README.md`：增加真实 Core 启动方式，明确 `mock-core` 仅为旧演示。
- `.gitignore`：忽略 `.pytest_cache/`，并继续确保 Core `.env`/dependencies/build 不被跟踪。
- `doc/core-postgresql-codex/codex-progress.md`：追加本轮与最终记录。

### Commands Run

```bash
cd core && npm run typecheck
cd core && npm run build
cd core && npm run db:migrate
cd core && npm run db:check
cd core && npm run dev
cd core && npm run seed:demo
cd core && npm run smoke
cd openclaw-plugin && npm run typecheck
cd openclaw-plugin && npm run test
cd openclaw-plugin && npm run build
cd openclaw-plugin && npm run demo:core
git diff --check
git check-ignore -v core/.env core/node_modules core/dist core/.pytest_cache
```

### Result

- Success。`seed:demo` 生成了包含 ALLOW/BLOCK/ASK/WARN 的可展示 run。
- `smoke` 的 12/12 项检查通过，覆盖方案要求的 11 项以及 decision detail。
- Core typecheck/build/db:migrate/db:check 通过。
- 插件 typecheck/build、6 files / 30 tests、`demo:core` 6/6 场景通过。
- 最终数据库核查：7 sessions、9 runs、26 tool calls、23 decisions、12 trace events、7 messages、5 tool results。
- 最终 raw 核查：raw params/payloads/results 全部为 0。
- `git diff --check` 通过；`core/.env`、`node_modules`、`dist`、`.pytest_cache` 均已忽略。

### Verification

- [x] API 文档完整
- [x] 11 张表用途文档
- [x] 前端/插件接入指南
- [x] 演示数据生成
- [x] smoke 12/12
- [x] Core 最终回归
- [x] 插件 30 tests 最终回归
- [x] 插件真实 Core 演示
- [x] raw 数据默认零持久化
- [x] Round 0-8 全部有记录

### Notes

- 当前机器未安装 Docker，因此 Compose 容器本身无法在此环境实跑；Compose 配置已完成，所有数据库与 API 验收均在同版本 PostgreSQL 16.14 临时本地实例上真实执行。
- 用户指定在 `doc` 下新建目录记录，因此方案中的 `docs/codex-progress.md`、`docs/core-db-design.md` 适配为 `doc/core-postgresql-codex/` 下的文件。

### Next Round

- Round 0-8 已全部完成。前端可按 `core-api-usage.md` 中的映射开始接入。

## Final Summary

- Core 接口：健康检查、runtime status、同步审计、批量事件、时间线、tool/decision 详情、证据路径、风险图、SSE。
- PostgreSQL：11 张核心表、基础索引/check 约束、4 条初始策略。
- 验收：Core smoke 12/12，插件 tests 30/30，插件 Core demo 6/6。

## Follow-up - Human Approval and Shared Event Queue

### Goal

- 允许用户对确实需要的破坏性 shell 命令进行明确审批，而不是无条件永久阻断。
- 修复 OpenClaw 重复注册插件时审计 Hook 与 flush worker 持有不同内存队列，导致异步事件丢失的问题。

### Design Decision

- TraceShield Core 负责返回 `ASK`、风险等级与审批元数据。
- TraceShield 插件负责将 `ASK` 映射为 OpenClaw `requireApproval`。
- OpenClaw Control UI/消息频道负责展示确认界面并路由审批结果。
- Eino 可在后续提供集中审批编排，但不是本地确认的必要依赖。
- 没有审批路由或超时时默认 `BLOCK`；Core 不可用时的插件 fallback 仍对高危命令返回 `BLOCK`。

### Files Added

- `openclaw-plugin/src/runtime/sharedEventQueue.ts`
- `openclaw-plugin/src/tests/shared-event-queue.test.ts`

### Files Changed

- `openclaw-plugin/src/index.ts`：多次插件注册共用进程级事件队列。
- `core/src/services/policyEngine.ts`：破坏性 shell 从 `BLOCK critical` 调整为 `ASK critical`，默认/超时动作均为 `BLOCK`。
- `core/src/db/seed_policies.sql`：策略更名为 `confirm_dangerous_shell_command`。
- `core/scripts/smoke_test.ts`、`openclaw-plugin/src/demo/openclawDemo.ts`：更新审批场景预期。
- `core/docs/api.md`、`doc/core-postgresql-codex/core-api-usage.md`、`README.md`：补充审批责任边界和宿主路由说明。

### Commands Run

```bash
cd openclaw-plugin && npm run typecheck && npm run test && npm run build
cd core && npm run typecheck && npm run build && npm run db:migrate && npm run db:check
cd core && npm run smoke
cd openclaw-plugin && npm run demo:core
openclaw gateway restart
openclaw agent --session-id ts-approval-proof-20260630 --message '<rm -rf approval test>' --json
psql <database-url> -c '<audit and event counts>'
```

### Result

- Success。Core smoke 12/12，其中 `rm -rf shell_exec -> ASK`。
- Success。插件 7 files / 31 tests 通过，Core demo 6/6 通过。
- 真实 OpenClaw 返回 `ASK critical`，命中 `confirm_dangerous_shell_command`，数据库保存完整 approval JSON。
- 纯 `openclaw agent` CLI 无对话频道/审批目标，因此 OpenClaw 报告 approval route unavailable 并安全拒绝；该行为符合默认 `BLOCK`。
- 共享队列修复后，真实 OpenClaw 事件已入库：`llm_input`、`before_tool_call`、`after_tool_call`、`llm_output`、`agent_end`。
- 最终核查：14 tool calls、13 decisions、9 trace events、5 messages、3 tool results；raw params/payloads/results 仍全为 0。

### Verification

- [x] 危险命令不再永久无条件 BLOCK
- [x] ASK 带 critical 风险和完整 approval
- [x] 无审批路由/超时默认拒绝
- [x] Core 失联 fallback 仍 fail-closed
- [x] 多次注册共用一个进程级事件队列
- [x] 真实 OpenClaw 异步事件入库
- [x] raw 数据默认不持久化
