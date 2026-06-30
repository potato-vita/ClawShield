# TraceShield Core + PostgreSQL 多轮 Codex 执行方案

> 目标：把当前 `mock-core` 演示服务升级为可落地的 `core` 服务雏形，完成 PostgreSQL 部署、数据库 schema、插件写入接口、查询接口，并为后续实时审计前端和 Eino 接入提供稳定 API。
>
> 执行原则：**多轮执行，每轮只做一组明确任务；每轮必须记录、测试、验证；验证失败不得进入下一轮。**

---

## 0. 总体方向

当前项目已有：

```text
openclaw-plugin/
  src/client/auditClient.ts       # POST /v1/audit/tool-call
  src/client/eventClient.ts       # POST /v1/events/batch
  src/types/event.ts              # TraceEvent / AuditRequest
  src/types/decision.ts           # AuditDecision
mock-core/
  server.ts                       # 现在只是演示服务
```

下一阶段要新增或改造：

```text
core/
  package.json
  tsconfig.json
  .env.example
  src/
    server.ts
    config.ts
    db/
      pool.ts
      migrate.ts
      check.ts
      schema.sql
      seed_policies.sql
    routes/
      health.ts
      audit.ts
      events.ts
      dashboard.ts
      queries.ts
    services/
      auditService.ts
      eventIngestService.ts
      policyEngine.ts
      evidenceService.ts
      riskGraphService.ts
      statsService.ts
    types/
      pluginContract.ts
      db.ts
  docs/
    api.md

docker-compose.yml
docs/codex-progress.md
```

推荐技术栈：

```text
Core: Node.js + TypeScript + Fastify + pg + zod
Database: PostgreSQL 16
数据传输: JSON / JSONB
实时推送: 后续 SSE，第一阶段先不做
```

---

## 1. 给 Codex 的总规则

每一轮都要把下面这段作为系统性要求贴给 Codex：

```text
你正在开发 TraceShield 项目。

必须遵守：
1. 不要一次性做完所有功能，只完成当前轮次要求。
2. 每轮结束必须更新 docs/codex-progress.md。
3. 每轮必须给出：
   - 修改了哪些文件
   - 新增了哪些文件
   - 执行了哪些命令
   - 命令是否成功
   - 如果失败，失败原因和修复方式
4. 每轮必须运行本轮指定验证命令。
5. 验证失败时，不要假装成功，不要进入下一轮。
6. 不要提交真实密钥，不要把 .env 加入 git。
7. 默认不保存 raw_payload、raw_params、raw_result；只在 debug 配置开启时保存。
8. 不要破坏 openclaw-plugin 现有测试和接口契约。
9. 保持与 openclaw-plugin 现有接口一致：
   - POST /v1/audit/tool-call
   - POST /v1/events/batch
   - AuditDecision: ALLOW / WARN / ASK / BLOCK
10. 所有接口返回 JSON。
```

---

# Round 0：仓库检查与执行记录文件

## 目标

先不要写业务功能。只做仓库检查、分支确认、记录文件创建。

## 给 Codex 的提示词

```text
Round 0：请检查当前 TraceShield 仓库结构，确认 openclaw-plugin 和 mock-core 是否存在。

任务：
1. 输出当前目录结构概要。
2. 创建 docs/codex-progress.md。
3. 在 docs/codex-progress.md 中记录 Round 0：
   - 当前分支
   - 当前仓库主要目录
   - Node 版本
   - npm 版本
   - 是否存在 openclaw-plugin/package.json
   - 是否存在 mock-core/package.json
4. 不要改业务代码。

验证命令：
- node -v
- npm -v
- ls
- test -f openclaw-plugin/package.json
- test -f mock-core/package.json || echo "mock-core package may not exist"

完成后停止，等待下一轮。
```

## 成功标准

```text
docs/codex-progress.md 存在
Round 0 有记录
没有改动业务代码
```

---

# Round 1：PostgreSQL 部署与数据库 Schema

## 目标

建立 PostgreSQL 环境和 schema，但暂时不写 Core API。

## 需要新增文件

```text
docker-compose.yml
core/.env.example
core/src/db/schema.sql
core/src/db/seed_policies.sql
core/package.json
core/tsconfig.json
core/src/db/check.ts
core/src/db/migrate.ts
```

## 数据库连接

`.env.example`：

```env
TRACESHIELD_DATABASE_URL=postgresql://traceshield:traceshield_dev_password@127.0.0.1:5432/traceshield
TRACESHIELD_CORE_PORT=8787
TRACESHIELD_SAVE_RAW_PAYLOAD=false
TRACESHIELD_SAVE_RAW_PARAMS=false
TRACESHIELD_SAVE_RAW_RESULT=false
```

`docker-compose.yml`：

```yaml
services:
  postgres:
    image: postgres:16
    container_name: traceshield-postgres
    environment:
      POSTGRES_DB: traceshield
      POSTGRES_USER: traceshield
      POSTGRES_PASSWORD: traceshield_dev_password
    ports:
      - "5432:5432"
    volumes:
      - traceshield_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U traceshield -d traceshield"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  traceshield_pgdata:
```

## schema.sql 需要包含这些表

```text
audit_sessions
audit_runs
trace_events
messages
tool_calls
tool_results
audit_decisions
audit_rule_hits
policies
evidence_items
evidence_steps
```

必须包含：

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

必须有基础索引和 check 约束。

## 给 Codex 的提示词

```text
Round 1：请新增 TraceShield Core 的 PostgreSQL 部署和数据库 schema。

任务：
1. 在仓库根目录创建 docker-compose.yml，启动 PostgreSQL 16。
2. 创建 core/ TypeScript 项目基础文件。
3. 创建 core/src/db/schema.sql。
4. 创建 core/src/db/seed_policies.sql，预置至少四条策略：
   - deny_secret_file_read
   - deny_dangerous_shell_command
   - ask_external_network_request
   - warn_unknown_tool
5. 创建 core/src/db/migrate.ts：
   - 读取 schema.sql 并执行
   - 读取 seed_policies.sql 并执行
6. 创建 core/src/db/check.ts：
   - 连接数据库
   - 查询当前数据库时间
   - 检查 11 张核心表是否存在
   - 检查 policies 是否有 seed 数据
7. 创建 core/.env.example。
8. 更新 docs/codex-progress.md，记录 Round 1 修改和验证结果。

验证命令：
- docker compose up -d postgres
- cd core && npm install
- cd core && cp .env.example .env
- cd core && npm run db:migrate
- cd core && npm run db:check

完成后停止，等待下一轮。
```

## 成功标准

```text
PostgreSQL 容器 healthy
db:migrate 成功
db:check 成功
11 张核心表存在
policies 至少 4 条
docs/codex-progress.md 已记录 Round 1
```

---

# Round 2：Core 服务骨架与健康检查

## 目标

搭建 `core` HTTP 服务，但暂时不做真实审计逻辑。

## 新增/修改文件

```text
core/src/server.ts
core/src/config.ts
core/src/db/pool.ts
core/src/routes/health.ts
core/src/routes/dashboard.ts
core/src/types/pluginContract.ts
```

## 接口

```http
GET /health
GET /v1/health
GET /v1/dashboard/runtime-status
```

`GET /v1/dashboard/runtime-status` 可以从数据库聚合真实数据，初始返回 0。

## 给 Codex 的提示词

```text
Round 2：请实现 TraceShield Core 服务骨架。

任务：
1. 使用 Fastify 实现 core/src/server.ts。
2. 从 .env 读取：
   - TRACESHIELD_DATABASE_URL
   - TRACESHIELD_CORE_PORT
   - TRACESHIELD_SAVE_RAW_PAYLOAD
   - TRACESHIELD_SAVE_RAW_PARAMS
   - TRACESHIELD_SAVE_RAW_RESULT
3. 实现 PostgreSQL pool。
4. 实现 GET /health 和 GET /v1/health：
   - 返回 ok、version、db_connected。
5. 实现 GET /v1/dashboard/runtime-status：
   - 返回 tool_calls_24h、blocked_24h、high_risk_24h、policy_hits_24h。
   - 没数据时返回 0。
6. 保留 mock-core，不要删除。
7. 更新 docs/codex-progress.md。

验证命令：
- cd core && npm run typecheck
- cd core && npm run build
- cd core && npm run dev
另开终端验证：
- curl http://127.0.0.1:8787/health
- curl http://127.0.0.1:8787/v1/dashboard/runtime-status

完成后停止，等待下一轮。
```

## 成功标准

```text
Core 能启动在 8787
/health 返回 ok
/v1/dashboard/runtime-status 返回合法 JSON
typecheck 和 build 通过
```

---

# Round 3：实现 /v1/audit/tool-call 入库与策略决策

## 目标

把插件同步审计接口做成真实接口。

## 策略规则第一版

```text
1. file_read 或 shell_exec 读取 .env / id_rsa / id_ed25519 / private_key / /etc/shadow → BLOCK critical
2. shell_exec 包含 rm -rf / mkfs / dd if= → BLOCK critical
3. network_request 且外部 URL → ASK medium
4. unknown → WARN medium
5. 其他 → ALLOW low
```

## 入库流程

```text
1. upsert audit_sessions
2. upsert audit_runs
3. upsert tool_calls
4. 执行 policyEngine
5. insert audit_decisions
6. insert audit_rule_hits
7. insert evidence_items
8. insert evidence_steps
9. 更新 audit_runs 聚合字段
10. 返回 AuditDecision
```

## 给 Codex 的提示词

```text
Round 3：请实现 POST /v1/audit/tool-call。

任务：
1. 在 core/src/types/pluginContract.ts 定义 AuditRequest、AuditDecision 类型。
2. 使用 zod 或手写校验验证 AuditRequest。
3. 实现 policyEngine：
   - deny_secret_file_read
   - deny_dangerous_shell_command
   - ask_external_network_request
   - warn_unknown_tool
   - default_allow
4. 实现 auditService：
   - upsert audit_sessions
   - upsert audit_runs
   - upsert tool_calls
   - insert audit_decisions
   - insert audit_rule_hits
   - insert evidence_items
   - insert evidence_steps
   - 更新 audit_runs 的 tool_call_count / blocked_count / warn_count / ask_count / risk_level / final_decision
5. 默认不保存 raw_params；只有 TRACESHIELD_SAVE_RAW_PARAMS=true 时保存。
6. 实现 POST /v1/audit/tool-call。
7. 为该接口增加最小测试脚本或 curl 示例。
8. 更新 docs/codex-progress.md。

验证命令：
- cd core && npm run typecheck
- cd core && npm run build
- cd core && npm run dev

另开终端执行 curl：
1. 正常读取 README.md，应返回 ALLOW
2. 读取 .env，应返回 BLOCK
3. shell rm -rf，应返回 BLOCK
4. http_request https://example.com，应返回 ASK
5. unknown tool，应返回 WARN

然后运行 SQL 或 db:check 确认：
- tool_calls 有记录
- audit_decisions 有记录
- audit_rule_hits 有记录
- evidence_steps 有记录

完成后停止，等待下一轮。
```

## 成功标准

```text
POST /v1/audit/tool-call 可用
五个场景返回符合预期
数据库有对应记录
插件 AuditClient 能解析返回结果
```

---

# Round 4：实现 /v1/events/batch 异步事件入库

## 目标

实现插件异步事件批量上报接口。

## 处理逻辑

```text
1. 对 events 数组逐条处理
2. event_id 幂等，重复上报不重复插入
3. 所有事件写入 trace_events
4. message_received / llm_input / llm_output / message_sending / agent_end 提取到 messages
5. after_tool_call 提取到 tool_results
6. fallback_decision 写入 trace_events，并可补充 audit_decisions 或 evidence
7. 更新 audit_sessions.last_seen_at
8. 返回 { ok: true, inserted, duplicated, extracted }
```

## 给 Codex 的提示词

```text
Round 4：请实现 POST /v1/events/batch。

任务：
1. 实现 eventIngestService。
2. 实现 trace_events 幂等入库，event_id 重复时跳过。
3. 提取消息类事件到 messages 表。
4. 提取 after_tool_call 到 tool_results 表。
5. 如果 after_tool_call 对应 tool_call_id 不存在，创建一个 placeholder tool_call，status='unknown'。
6. 默认不保存 raw_payload 和 raw_result；只有配置开启时保存。
7. 实现 POST /v1/events/batch。
8. 返回 inserted、duplicated、message_extracted、tool_result_extracted。
9. 更新 docs/codex-progress.md。

验证命令：
- cd core && npm run typecheck
- cd core && npm run build
- cd core && npm run dev

curl 验证：
1. 发送 message_received 事件，应写入 trace_events 和 messages。
2. 发送 after_tool_call 事件，应写入 trace_events 和 tool_results。
3. 重复发送同一个 event_id，不应重复插入。
4. 查询数据库确认数量正确。

完成后停止，等待下一轮。
```

## 成功标准

```text
/v1/events/batch 可用
重复 event_id 幂等
messages 能被提取
tool_results 能被提取
数据库数量正确
```

---

# Round 5：实现前端需要的查询 API

## 目标

让实时审计控制台可以开始接数据。

## 接口

```http
GET /v1/audit/events?limit=50
GET /v1/tool-calls/:toolCallId
GET /v1/tool-calls/:toolCallId/decision
GET /v1/runs/:runId/evidence-path
GET /v1/runs/:runId/risk-graph
GET /v1/dashboard/runtime-status
```

## 风险图生成规则

第一版不落库，查询时生成：

```text
1. 从 tool_calls 查询 run_id 下所有调用，按 started_at 排序。
2. 第一个节点是 User Request。
3. 每个工具调用一个节点。
4. 如果有 BLOCK / ASK / WARN，节点标风险等级。
5. 顺序相邻节点生成 flow edge。
6. 如果有 evidence_steps，把证据作为附加节点或 node metadata。
```

## 给 Codex 的提示词

```text
Round 5：请实现前端查询 API。

任务：
1. 实现 GET /v1/audit/events?limit=50。
   - 返回左侧审计时间线需要的数据。
2. 实现 GET /v1/tool-calls/:toolCallId。
3. 实现 GET /v1/tool-calls/:toolCallId/decision。
   - 返回工具调用、审计决策、规则命中。
4. 实现 GET /v1/runs/:runId/evidence-path。
5. 实现 GET /v1/runs/:runId/risk-graph。
   - 风险图查询时动态生成，不写入数据库。
6. 确保 GET /v1/dashboard/runtime-status 返回真实聚合结果。
7. 更新 docs/codex-progress.md。

验证命令：
- cd core && npm run typecheck
- cd core && npm run build
- cd core && npm run dev

curl 验证：
- curl http://127.0.0.1:8787/v1/dashboard/runtime-status
- curl http://127.0.0.1:8787/v1/audit/events
- curl http://127.0.0.1:8787/v1/runs/<run_id>/risk-graph
- curl http://127.0.0.1:8787/v1/runs/<run_id>/evidence-path
- curl http://127.0.0.1:8787/v1/tool-calls/<tool_call_id>/decision

完成后停止，等待下一轮。
```

## 成功标准

```text
前端所需 6 个查询接口可用
runtime-status 有真实统计
audit/events 能看到最近工具调用
risk-graph 返回 nodes 和 edges
evidence-path 返回 steps
decision 返回规则命中详情
```

---

# Round 6：接 openclaw-plugin 真实联调

## 目标

让现有插件从 mock-core 切换到真实 core。

## 给 Codex 的提示词

```text
Round 6：请联调 openclaw-plugin 与新的 core 服务。

任务：
1. 确认 openclaw-plugin 不需要修改接口路径。
2. 启动 PostgreSQL 和 core。
3. 设置 openclaw-plugin 环境变量 TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787。
4. 运行 openclaw-plugin 的 typecheck、test、demo:openclaw。
5. 如果 demo 依赖 mock-core，请新增一个 demo:core 或说明如何让 demo 连接真实 core。
6. 验证数据库中：
   - tool_calls 有数据
   - audit_decisions 有数据
   - trace_events 有数据
7. 更新 docs/codex-progress.md。

验证命令：
- docker compose up -d postgres
- cd core && npm run db:migrate
- cd core && npm run dev
- cd openclaw-plugin && npm run typecheck
- cd openclaw-plugin && npm run test
- cd openclaw-plugin && TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787 npm run demo:openclaw
- cd core && npm run db:check

完成后停止，等待下一轮。
```

## 成功标准

```text
openclaw-plugin 不再依赖 mock-core 也能跑 demo
真实 core 返回 ALLOW/BLOCK/ASK/WARN
数据库中有插件产生的数据
```

---

# Round 7：SSE 实时推送接口

## 目标

给前端实时审计控制台提供实时事件流。

## 接口

```http
GET /v1/stream/audit-events
```

第一版可以用内存广播：

```text
POST /v1/audit/tool-call 成功后广播 audit_event
POST /v1/events/batch 成功后广播 trace_event
```

## 给 Codex 的提示词

```text
Round 7：请实现 SSE 实时推送接口。

任务：
1. 实现 GET /v1/stream/audit-events。
2. 客户端连接后保持 SSE。
3. /v1/audit/tool-call 产生审计决策后广播 audit_event。
4. /v1/events/batch 产生新事件后广播 trace_event。
5. 定期发送 heartbeat，避免连接被关闭。
6. 更新 docs/codex-progress.md。

验证命令：
- cd core && npm run typecheck
- cd core && npm run build
- cd core && npm run dev

另开终端：
- curl -N http://127.0.0.1:8787/v1/stream/audit-events

再开一个终端发送 /v1/audit/tool-call 请求。
确认 SSE 终端能收到 audit_event。

完成后停止，等待下一轮。
```

## 成功标准

```text
SSE 可连接
发送 audit/tool-call 后前端流能收到事件
不会影响原有 API
```

---

# Round 8：文档、种子数据与最终验收脚本

## 目标

整理项目，让后续前端和 Eino 可以接。

## 新增

```text
core/docs/api.md
core/scripts/seed_demo_data.ts
core/scripts/smoke_test.ts
docs/core-db-design.md
docs/core-api-usage.md
```

## smoke test 内容

必须自动完成：

```text
1. 检查 /health
2. 发送正常 file_read → ALLOW
3. 发送 .env file_read → BLOCK
4. 发送 rm -rf shell_exec → BLOCK
5. 发送 external network_request → ASK
6. 发送 message_received event
7. 发送 after_tool_call event
8. 查询 dashboard runtime-status
9. 查询 audit/events
10. 查询 risk-graph
11. 查询 evidence-path
```

## 给 Codex 的提示词

```text
Round 8：请补充文档、种子数据和最终验收脚本。

任务：
1. 创建 core/docs/api.md，记录所有已实现接口。
2. 创建 docs/core-db-design.md，记录数据库表用途。
3. 创建 core/scripts/seed_demo_data.ts，用于生成一组可供前端展示的数据。
4. 创建 core/scripts/smoke_test.ts，自动调用所有核心接口并验证返回。
5. package.json 增加：
   - npm run seed:demo
   - npm run smoke
6. 更新 docs/codex-progress.md。
7. 不要删除 mock-core，但 README 中说明 mock-core 仅用于旧演示。

验证命令：
- docker compose up -d postgres
- cd core && npm run db:migrate
- cd core && npm run dev
- cd core && npm run seed:demo
- cd core && npm run smoke

完成后输出最终总结：
- 已实现接口
- 已创建表
- 验证命令结果
- 前端下一步如何接入
```

## 成功标准

```text
smoke test 一键通过
api.md 完整
seed_demo_data 能生成前端可展示数据
docs/codex-progress.md 有 Round 0-8 全部记录
```

---

# 每轮必须记录的格式

`docs/codex-progress.md` 建议格式：

````markdown
# TraceShield Codex Progress

## Round 0 - Repository Check

### Goal
...

### Files Changed
- ...

### Commands Run
```bash
node -v
npm -v
```

### Result
- Success / Failed

### Verification
- [x] ...
- [ ] ...

### Notes
...

### Next Round
...
````

每一轮都要追加，不要覆盖前面的记录。

---

# 最终验收标准

全部完成后，应该可以跑：

```bash
docker compose up -d postgres

cd core
cp .env.example .env
npm install
npm run db:migrate
npm run dev
```

然后另开终端：

```bash
cd core
npm run smoke
```

再联调插件：

```bash
cd openclaw-plugin
TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787 npm run demo:openclaw
```

最终应该满足：

```text
1. Core 正常启动
2. PostgreSQL 正常连接
3. 插件同步审计能返回 ALLOW / BLOCK / ASK / WARN
4. 事件批量上报能入库
5. Dashboard 查询接口能返回统计
6. Audit Timeline 查询接口能返回工具调用列表
7. Decision 查询接口能返回规则命中
8. Evidence Path 查询接口能返回路径步骤
9. Risk Graph 查询接口能返回 nodes / edges
10. SSE 能推送实时审计事件
```

---

# 不要让 Codex 做的事情

这次任务里不要让 Codex 做：

```text
1. 不要开发完整前端页面。
2. 不要接 Eino。
3. 不要实现复杂登录系统。
4. 不要实现完整用户/agent 管理。
5. 不要把 mock-core 删除。
6. 不要保存真实 secret。
7. 不要把 .env 提交进仓库。
8. 不要把风险图提前落库。
9. 不要把所有 raw payload 默认存数据库。
10. 不要破坏 openclaw-plugin 现有测试。
```

---

# 建议你实际执行时的节奏

如果你用 Codex CLI，可以这样做：

```text
第一次输入：Round 0
成功后确认，再输入 Round 1
Round 1 成功后再输入 Round 2
...
```

不要一次性把 Round 0-8 全部丢给 Codex 执行。这个任务太大，一次性执行失败概率很高。

每轮完成后你检查：

```text
1. docs/codex-progress.md 有没有更新
2. 本轮验证命令有没有真的跑
3. 数据库有没有真实记录
4. 接口返回是否符合插件现有契约
5. 是否误改 openclaw-plugin
```

---

# 第一版完成后前端如何接

前端第一版只需要接这些 API：

```text
顶部卡片：
GET /v1/dashboard/runtime-status

左侧事件流：
GET /v1/audit/events?limit=50

中间风险图：
GET /v1/runs/:runId/risk-graph

右侧决策详情：
GET /v1/tool-calls/:toolCallId/decision

底部证据路径：
GET /v1/runs/:runId/evidence-path

实时更新：
GET /v1/stream/audit-events
```

这样实时审计控制台就可以开始落地。
