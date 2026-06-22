# TraceShield Core 与前端数据库联动执行任务书

> 交付对象：Codex / Claude Code / 组内开发成员  
> 当前阶段：在插件已经完成 MVP 的前提下，开发 Core，使其替代 mock-core，并支撑三栏式前端工作台。  
> 核心要求：每一轮都必须有测试；每一轮尽量保持插件、Core、前端至少一条链路能跑通；禁止连续多轮只写后端但不联调。

---

## 0. 背景与目标

当前项目已经有 OpenClaw 插件 MVP，插件负责：

1. 在 `before_tool_call` 同步请求审计接口。
2. 在 `after_tool_call` 和消息类 hook 中异步上传事件。
3. 根据 Core 返回的 `ALLOW / WARN / ASK / BLOCK / MODIFY` 执行放行、提示、审批、阻断或改参。
4. 支持本地降级、脱敏、队列补传和基础测试。

现在要做的 Core 不是一个孤立后端，而是要同时服务三方：

```text
OpenClaw Plugin  →  Core  →  Database
                         ↓
                  Eino / 前端工作台
```

本阶段最终目标：

```text
1. 插件不再调用 mock-core，而是调用真实 Core。
2. Core 能接收插件同步审计请求并返回真实决策。
3. Core 能接收插件异步事件并持久化。
4. Core 能把工具调用、审计结果、安全事件保存到 SQLite。
5. 前端左侧能显示会话。
6. 前端中间能显示聊天分析和工具调用链。
7. 前端右侧能显示某一次事件或工具调用的详情。
8. 仪表盘能根据真实数据库统计高危事件、趋势、用户、部门和渠道。
9. 每一轮都有自动化测试和手工联调记录。
```

---

## 1. 总体技术路线

### 1.1 推荐技术栈

开发阶段使用：

```text
Python 3.11+
FastAPI
Uvicorn
SQLAlchemy 2.x
SQLite
Pydantic v2
pytest
httpx
```

原因：

```text
1. 插件已经是 TypeScript，Core 不必再强行用 TypeScript。
2. Python 更适合快速搬实验代码里的规则、风险图和审计逻辑。
3. SQLite 足够支持答辩和本地演示。
4. 后续如果需要 PostgreSQL，SQLAlchemy 模型可以迁移。
```

### 1.2 目录结构

请在仓库根目录下创建或整理为：

```text
TraceShield/
  openclaw-plugin/                 # 已有插件，不要随意大改协议
  mock-core/                       # 保留，用于对比，不再作为主服务
  core/
    README.md
    requirements.txt
    pyproject.toml                 # 可选
    .env.example
    app/
      main.py
      config.py
      logging.py
      db/
        base.py
        session.py
        models.py
        init_db.py
        repositories.py
        seed.py
      schemas/
        plugin.py
        module4.py
        sessions.py
        reports.py
      services/
        audit_engine.py
        rule_engine.py
        event_ingest.py
        event_projector.py
        dashboard_service.py
        event_detail_service.py
        report_service.py
        session_service.py
        sanitizer.py
        idgen.py
      api/
        health.py
        audit.py
        events.py
        module4.py
        sessions.py
        reports.py
      static/
        index.html                 # 可以放用户提供的前端 HTML
      data/
        .gitkeep
        uploads/
          .gitkeep
        exports/
          .gitkeep
        queue/
          .gitkeep
    tests/
      conftest.py
      test_health.py
      test_db_models.py
      test_audit_api.py
      test_event_ingest.py
      test_dashboard_api.py
      test_event_detail_api.py
      test_sessions_api.py
      test_reports_api.py
      test_plugin_contract.py
      test_integration_plugin_flow.py
    scripts/
      dev_run.sh
      reset_db.sh
      smoke_plugin_core.sh
      smoke_frontend_api.sh
```

---

## 2. 硬性原则

### 2.1 不许破坏插件协议

插件目前应该已经能调用：

```http
POST /v1/audit/tool-call
POST /v1/events/batch
```

Core 必须兼容这两个接口。除非先修改插件测试，并证明新旧协议兼容，否则不要改字段名。

### 2.2 Core 第一版只替代 mock-core

第一版不要做复杂图数据库，不要做完整策略 DSL，不要做用户权限系统。

第一版只做：

```text
同步审计 + 事件入库 + 工具调用入库 + 审计结果入库 + 安全事件生成 + 前端查询
```

### 2.3 每轮都要测试

每一轮至少包含：

```text
1. 单元测试
2. API 测试
3. 数据库持久化测试
4. 插件联调测试，至少 curl 模拟插件请求
5. 如涉及前端接口，必须用前端实际调用的 API 路径测试
```

### 2.4 不保存敏感原文

默认不要把完整 token、密码、私钥、完整文件内容写入数据库。

数据库保存：

```text
preview
hash
size
redacted text
summary
```

不要保存：

```text
完整 .env
完整私钥
完整 cookie
完整 access token
完整文件内容
```

### 2.5 所有结论以测试为准

开发者、Codex、Claude Code 的判断都不算最终依据。最终依据是：

```bash
pytest
curl smoke
插件 demo
前端接口返回
数据库记录
```

---

## 3. Core 必须实现的接口

### 3.1 插件接口

#### 3.1.1 同步审计接口

```http
POST /v1/audit/tool-call
```

请求示例：

```json
{
  "schema_version": "v1",
  "session_id": "sess_001",
  "run_id": "run_001",
  "trace_id": "trace_001",
  "tool_call_id": "call_001",
  "tool_name": "exec",
  "tool_kind": "shell_exec",
  "params": {
    "cmd": "cat .env"
  },
  "context": {
    "user_goal": "检查项目配置",
    "recent_messages": []
  },
  "timestamp": "2026-06-22T10:00:00Z"
}
```

响应示例：

```json
{
  "decision": "BLOCK",
  "risk_level": "critical",
  "risk_score": 95.0,
  "reason": "命令尝试读取敏感环境变量文件 .env",
  "matched_rules": ["secret_file_read", "sensitive_env_access"],
  "modified_params": null,
  "approval": null,
  "evidence": [
    {
      "type": "sensitive_path",
      "key": "path",
      "value": ".env",
      "description": "工具参数中包含敏感配置文件路径"
    }
  ]
}
```

#### 3.1.2 异步事件批量上传接口

```http
POST /v1/events/batch
```

请求示例：

```json
{
  "events": [
    {
      "event_id": "evt_001",
      "schema_version": "v1",
      "type": "before_tool_call",
      "session_id": "sess_001",
      "run_id": "run_001",
      "trace_id": "trace_001",
      "timestamp": "2026-06-22T10:00:00Z",
      "payload": {
        "tool_call_id": "call_001",
        "tool_name": "exec",
        "tool_kind": "shell_exec",
        "params": {
          "cmd": "cat .env"
        }
      }
    }
  ]
}
```

响应示例：

```json
{
  "success": true,
  "accepted": 1,
  "duplicated": 0,
  "failed": 0
}
```

### 3.2 前端接口

用户给出的 HTML 已经调用这些路径，Core 必须尽量适配：

```http
GET  /api/module4/health
GET  /api/module4/dashboard?time_range=7d
GET  /api/module4/events/{event_id}
GET  /api/module4/exports/{filename}

GET    /sessions
POST   /sessions
DELETE /sessions/{session_id}
GET    /sessions/{session_id}/render
POST   /sessions/{session_id}/chat
POST   /sessions/{session_id}/docs
POST   /sessions/{session_id}/approve
POST   /sessions/{session_id}/abort
```

第一版可以不接真实大模型，但这些接口不能 404。

---

## 4. 数据库设计

### 4.1 第一阶段必须实现的 8 张表

```text
analysis_sessions
chat_messages
openclaw_runs
trace_events
tool_calls
tool_results
audit_decisions
security_events
```

### 4.2 第二阶段再实现的表

```text
risk_evidence
risk_graph_edges
reports
uploaded_documents
policies
approvals
```

本任务书会在前 6 轮完成第一阶段 8 张表，并在后续轮次逐步补第二阶段表。

---

## 5. 第一阶段数据库 DDL

Codex 可以选择 SQLAlchemy 模型实现，但字段必须覆盖以下 DDL。

### 5.1 analysis_sessions

```sql
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'eino',
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    last_message_at DATETIME,
    summary TEXT,
    metadata_json TEXT
);
```

### 5.2 chat_messages

```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'markdown',
    parent_id TEXT,
    order_index INTEGER NOT NULL,
    related_tool_call_id TEXT,
    related_event_id TEXT,
    related_report_id TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);
```

### 5.3 openclaw_runs

```sql
CREATE TABLE IF NOT EXISTS openclaw_runs (
    id TEXT PRIMARY KEY,
    analysis_session_id TEXT,
    openclaw_session_id TEXT,
    user_goal TEXT,
    status TEXT NOT NULL,
    started_at DATETIME NOT NULL,
    ended_at DATETIME,
    total_tool_calls INTEGER DEFAULT 0,
    blocked_count INTEGER DEFAULT 0,
    ask_count INTEGER DEFAULT 0,
    warn_count INTEGER DEFAULT 0,
    metadata_json TEXT,
    FOREIGN KEY (analysis_session_id) REFERENCES analysis_sessions(id)
);
```

### 5.4 trace_events

```sql
CREATE TABLE IF NOT EXISTS trace_events (
    id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    event_type TEXT NOT NULL,
    session_id TEXT,
    run_id TEXT,
    trace_id TEXT,
    source TEXT NOT NULL DEFAULT 'openclaw-plugin',
    severity TEXT DEFAULT 'info',
    payload_json TEXT NOT NULL,
    payload_hash TEXT,
    created_at DATETIME NOT NULL,
    received_at DATETIME NOT NULL
);
```

### 5.5 tool_calls

```sql
CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    session_id TEXT,
    trace_id TEXT,
    tool_name TEXT NOT NULL,
    tool_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    decision TEXT,
    raw_params_json TEXT,
    sanitized_params_json TEXT,
    param_summary TEXT,
    resource_type TEXT,
    resource_value TEXT,
    started_at DATETIME NOT NULL,
    ended_at DATETIME,
    latency_ms INTEGER,
    FOREIGN KEY (run_id) REFERENCES openclaw_runs(id)
);
```

### 5.6 tool_results

```sql
CREATE TABLE IF NOT EXISTS tool_results (
    id TEXT PRIMARY KEY,
    tool_call_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    exit_code INTEGER,
    result_preview TEXT,
    result_hash TEXT,
    result_size INTEGER,
    error_message TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id)
);
```

### 5.7 audit_decisions

```sql
CREATE TABLE IF NOT EXISTS audit_decisions (
    id TEXT PRIMARY KEY,
    tool_call_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score REAL,
    reason TEXT NOT NULL,
    matched_rules_json TEXT,
    modified_params_json TEXT,
    fallback_used BOOLEAN DEFAULT FALSE,
    core_latency_ms INTEGER,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id)
);
```

### 5.8 security_events

```sql
CREATE TABLE IF NOT EXISTS security_events (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    run_id TEXT,
    tool_call_id TEXT,
    audit_decision_id TEXT,
    event_title TEXT NOT NULL,
    event_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score REAL NOT NULL,
    event_status TEXT NOT NULL DEFAULT 'open',
    username TEXT,
    department_name TEXT,
    host_name TEXT,
    ip_address TEXT,
    file_name TEXT,
    file_path TEXT,
    sensitive_type TEXT,
    sensitive_level TEXT,
    operation TEXT,
    process_name TEXT,
    target TEXT,
    target_type TEXT,
    risk_explanation TEXT,
    recommended_actions_json TEXT,
    occurred_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id),
    FOREIGN KEY (audit_decision_id) REFERENCES audit_decisions(id)
);
```

---

## 6. 多轮开发计划

下面所有轮次都要求 Codex 在完成后输出：

```text
1. 本轮修改了哪些文件
2. 新增了哪些测试
3. 执行了哪些命令
4. 哪些通过
5. 哪些失败以及原因
6. 下一轮风险点
```

---

# 第 0 轮：建立 Core 开发基线，不写业务

## 目标

确认当前插件状态，把 Core 目录搭起来，但不实现复杂业务。

## 任务

1. 在仓库根目录创建 `core/`。
2. 创建 Python 虚拟环境说明。
3. 创建 `requirements.txt`。
4. 创建 FastAPI 最小应用。
5. 添加 `/api/module4/health`。
6. 添加测试框架。
7. 不连接数据库，不实现审计。

## 文件

```text
core/requirements.txt
core/app/main.py
core/app/api/health.py
core/app/config.py
core/tests/conftest.py
core/tests/test_health.py
core/README.md
```

## requirements.txt

至少包含：

```txt
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
pytest
pytest-asyncio
httpx
python-multipart
```

## 健康检查接口

```http
GET /api/module4/health
```

返回：

```json
{
  "success": true,
  "database": "not_initialized",
  "service": "traceshield-core",
  "version": "0.1.0"
}
```

## 测试

```bash
cd core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
curl http://127.0.0.1:8000/api/module4/health
```

## 插件联调测试

本轮 Core 还没有 `/v1/audit/tool-call`，但要确认插件当前测试仍然通过：

```bash
cd openclaw-plugin
npm install
npm run typecheck
npm test
npm run build
```

如果插件脚本名称不同，Codex 必须先读取 `package.json`，使用实际存在的脚本。

## 验收标准

```text
1. core 可以启动。
2. /api/module4/health 返回 200。
3. pytest 至少 1 个测试通过。
4. 插件原有测试仍然通过。
5. 本轮不能修改插件协议。
```

## Codex 执行指令

```text
请执行第 0 轮：为 TraceShield 创建 core FastAPI 最小服务。
只实现健康检查和测试框架，不实现数据库和审计业务。
完成后运行 core 的 pytest，并运行 openclaw-plugin 的 typecheck/test/build，确认没有破坏插件。
请输出修改文件、测试命令和测试结果。
```

---

# 第 1 轮：数据库初始化与 8 张核心表

## 目标

让 Core 拥有 SQLite 数据库，并创建第一阶段 8 张核心表。

## 任务

1. 实现数据库配置。
2. 实现 SQLAlchemy Base。
3. 实现 8 张表的 ORM 模型。
4. 实现 `init_db()`。
5. 实现 `scripts/reset_db.sh`。
6. 更新 `/api/module4/health`，能检查数据库。

## 文件

```text
core/app/db/base.py
core/app/db/session.py
core/app/db/models.py
core/app/db/init_db.py
core/scripts/reset_db.sh
core/tests/test_db_models.py
core/tests/test_health.py
```

## 配置要求

默认数据库路径：

```text
core/app/data/traceshield.db
```

可通过环境变量覆盖：

```text
TRACESHIELD_DATABASE_URL=sqlite:///./app/data/traceshield.db
```

## 健康检查返回

数据库正常时：

```json
{
  "success": true,
  "database": "ok",
  "service": "traceshield-core",
  "version": "0.1.0"
}
```

数据库异常时：

```json
{
  "success": false,
  "database": "error",
  "error": "..."
}
```

## 测试

### 单元测试

```bash
cd core
pytest -q tests/test_db_models.py tests/test_health.py
```

测试内容：

```text
1. 8 张表能创建。
2. analysis_sessions 能插入和查询。
3. tool_calls 能插入和查询。
4. audit_decisions 能插入和查询。
5. security_events 能插入和查询。
6. health 能返回 database=ok。
```

### 手工验证

```bash
cd core
bash scripts/reset_db.sh
sqlite3 app/data/traceshield.db ".tables"
curl http://127.0.0.1:8000/api/module4/health
```

期望 `.tables` 至少包含：

```text
analysis_sessions
chat_messages
openclaw_runs
trace_events
tool_calls
tool_results
audit_decisions
security_events
```

## 插件联调测试

本轮仍然不接插件业务，但要保证插件还能构建：

```bash
cd openclaw-plugin
npm run typecheck
npm test
npm run build
```

## 验收标准

```text
1. 数据库文件能生成。
2. 8 张表存在。
3. health 显示 Database OK。
4. core 测试通过。
5. 插件测试仍通过。
```

## Codex 执行指令

```text
请执行第 1 轮：为 TraceShield Core 增加 SQLite 数据库和 8 张核心表。
使用 SQLAlchemy 2.x，实现 models、session、init_db 和 reset_db 脚本。
更新 /api/module4/health，使其检查数据库状态。
补充 pytest，验证建表和基础插入查询。
完成后运行 core 测试和 openclaw-plugin 测试。
```

---

# 第 2 轮：实现插件协议 Schema，不写复杂规则

## 目标

用 Pydantic 固化插件和 Core 之间的协议，避免后面字段漂移。

## 任务

1. 实现 `AuditToolCallRequest`。
2. 实现 `AuditDecisionResponse`。
3. 实现 `TraceEvent`。
4. 实现 `EventBatchRequest`。
5. 实现字段兼容：同时兼容 `type` 和 `event_type`。
6. 写协议测试。

## 文件

```text
core/app/schemas/plugin.py
core/tests/test_plugin_contract.py
```

## Schema 要求

### AuditToolCallRequest

必须支持字段：

```text
schema_version
session_id
run_id
trace_id
tool_call_id
tool_name
tool_kind
params
context
timestamp
```

### AuditDecisionResponse

必须支持字段：

```text
decision
risk_level
risk_score
reason
matched_rules
modified_params
approval
evidence
```

### TraceEvent

必须支持字段：

```text
event_id
schema_version
type / event_type
session_id
run_id
trace_id
timestamp
payload
```

## 测试

```bash
cd core
pytest -q tests/test_plugin_contract.py
```

测试用例：

```text
1. 标准 AuditToolCallRequest 能解析。
2. params 为空对象时能解析。
3. context 缺失时使用默认值。
4. TraceEvent 使用 type 字段能解析。
5. TraceEvent 使用 event_type 字段能解析。
6. AuditDecisionResponse 能序列化成插件需要的 JSON。
```

## 插件联调测试

从插件测试或文档中找一份实际 audit 请求样例，保存为：

```text
core/tests/fixtures/plugin_audit_request.json
```

用这个 fixture 测试 Core schema 是否能解析。

如果插件仓库没有 fixture，Codex 需要从 `openclaw-plugin/src/types` 或测试里提取字段，生成一份最小真实样例。

## 验收标准

```text
1. Core schema 与插件字段一致。
2. 插件实际样例能被 Core 解析。
3. 测试通过。
4. 不实现复杂审计，只固化协议。
```

## Codex 执行指令

```text
请执行第 2 轮：为 TraceShield Core 实现插件协议 Pydantic Schema。
必须读取 openclaw-plugin 中已有 TypeScript 类型或测试样例，确保字段兼容。
实现 tests/test_plugin_contract.py，使用真实插件样例验证协议。
不要实现复杂审计逻辑。
```

---

# 第 3 轮：实现 /v1/audit/tool-call，替代 mock-core

## 目标

Core 第一次真正替代 mock-core。插件可以请求真实 Core，并得到 ALLOW/BLOCK/ASK/WARN。

## 任务

1. 实现 `POST /v1/audit/tool-call`。
2. 实现最小规则引擎。
3. 保存 `openclaw_runs`。
4. 保存 `tool_calls`。
5. 保存 `audit_decisions`。
6. BLOCK/ASK/WARN 生成 `security_events`。
7. 返回插件兼容响应。

## 最小规则

必须实现：

```text
1. cmd 包含 rm -rf               → BLOCK / critical / 99
2. cmd 或 path 包含 .env          → BLOCK / critical / 95
3. cmd 或 path 包含 id_rsa        → BLOCK / critical / 98
4. url 包含 external-upload.com   → ASK / high / 80
5. tool_kind 是 network_request 且外部域名未知 → ASK / high / 75
6. 普通 read_file README.md       → ALLOW / low / 5
7. 未知工具                       → WARN / medium / 50
```

## 生成 security_events 的规则

当 decision 为 `BLOCK / ASK / WARN` 时生成 `security_events`。

```text
event_type       根据工具类型生成，例如 sensitive_file_access / dangerous_command / external_upload
event_title      由规则生成，例如 “阻止读取敏感文件 .env”
risk_level       来自 audit decision
risk_score       来自 audit decision
event_status     默认 open
occurred_at       请求 timestamp 或当前时间
```

## API 测试

```bash
cd core
pytest -q tests/test_audit_api.py
```

必须覆盖：

```text
1. rm -rf 返回 BLOCK。
2. cat .env 返回 BLOCK。
3. cat ~/.ssh/id_rsa 返回 BLOCK。
4. external-upload.com 返回 ASK。
5. README.md 返回 ALLOW。
6. 未知工具返回 WARN。
7. BLOCK 时数据库生成 tool_calls、audit_decisions、security_events。
8. ALLOW 时数据库生成 tool_calls、audit_decisions，但不一定生成 security_events。
```

## 手工 curl 测试

启动 Core：

```bash
cd core
uvicorn app.main:app --reload --port 8000
```

执行：

```bash
curl -s -X POST http://127.0.0.1:8000/v1/audit/tool-call \
  -H 'Content-Type: application/json' \
  -d '{
    "schema_version":"v1",
    "session_id":"sess_smoke",
    "run_id":"run_smoke",
    "trace_id":"trace_smoke",
    "tool_call_id":"call_smoke_env",
    "tool_name":"exec",
    "tool_kind":"shell_exec",
    "params":{"cmd":"cat .env"},
    "context":{"user_goal":"检查配置"},
    "timestamp":"2026-06-22T10:00:00Z"
  }'
```

期望包含：

```json
{
  "decision": "BLOCK",
  "risk_level": "critical"
}
```

## 插件联调测试

把插件配置里的 Core 地址指向真实 Core：

```text
http://127.0.0.1:8000
```

执行插件已有 demo 或测试。如果已有 `demo:openclaw`，运行：

```bash
cd openclaw-plugin
npm run demo:openclaw
```

如果没有该脚本，Codex 需要创建或使用现有脚本模拟一次 `before_tool_call`，至少包含：

```text
1. read README.md → ALLOW
2. cat .env → BLOCK
3. rm -rf /tmp/x → BLOCK
4. external-upload.com → ASK
```

## 数据库验证

```bash
sqlite3 core/app/data/traceshield.db "select id, tool_name, decision, status from tool_calls order by started_at desc limit 5;"
sqlite3 core/app/data/traceshield.db "select id, risk_level, event_title from security_events order by created_at desc limit 5;"
```

## 验收标准

```text
1. /v1/audit/tool-call 返回插件可识别 JSON。
2. 插件请求真实 Core 后能阻断危险行为。
3. 数据库有 tool_calls 和 audit_decisions。
4. BLOCK/ASK/WARN 能生成 security_events。
5. pytest 通过。
6. 插件联调通过。
```

## Codex 执行指令

```text
请执行第 3 轮：实现真实 /v1/audit/tool-call，替代 mock-core。
实现最小规则引擎，覆盖 rm -rf、.env、id_rsa、external-upload.com、README.md 和未知工具。
每次审计必须保存 openclaw_runs、tool_calls、audit_decisions，并在 BLOCK/ASK/WARN 时生成 security_events。
实现 pytest 和 curl smoke，并运行插件联调，证明插件可以从真实 Core 获得 BLOCK/ASK/ALLOW。
```

---

# 第 4 轮：实现 /v1/events/batch 异步事件入库

## 目标

插件异步上传的消息、工具结果、任务结束事件能持久化，并能投影到工具调用和结果表。

## 任务

1. 实现 `POST /v1/events/batch`。
2. 保存所有事件到 `trace_events`。
3. 支持 `event_id` 幂等去重。
4. 对 `before_tool_call` 事件更新或创建 `tool_calls`。
5. 对 `after_tool_call` 事件创建 `tool_results`。
6. 对 `agent_end` 事件更新 `openclaw_runs.status`。
7. 返回 accepted/duplicated/failed。

## Event 类型处理

```text
message_received  → 只进 trace_events
llm_input          → 只进 trace_events
llm_output         → 只进 trace_events
before_tool_call   → trace_events + tool_calls upsert
after_tool_call    → trace_events + tool_results insert/update
audit_decision     → trace_events + audit_decisions upsert
fallback_used      → trace_events + security_events
agent_end          → trace_events + openclaw_runs ended_at/status
```

## API 测试

```bash
cd core
pytest -q tests/test_event_ingest.py
```

必须覆盖：

```text
1. 单事件上传成功 accepted=1。
2. 重复 event_id 上传 duplicated=1。
3. before_tool_call 能创建 tool_calls。
4. after_tool_call 能创建 tool_results。
5. agent_end 能更新 run 状态。
6. 批量事件中一个坏事件不影响其他好事件。
```

## 手工 curl 测试

```bash
curl -s -X POST http://127.0.0.1:8000/v1/events/batch \
  -H 'Content-Type: application/json' \
  -d '{
    "events": [
      {
        "event_id":"evt_smoke_before_001",
        "schema_version":"v1",
        "type":"before_tool_call",
        "session_id":"sess_smoke",
        "run_id":"run_smoke",
        "trace_id":"trace_smoke",
        "timestamp":"2026-06-22T10:00:01Z",
        "payload":{
          "tool_call_id":"call_smoke_001",
          "tool_name":"read_file",
          "tool_kind":"file_read",
          "params":{"path":"README.md"}
        }
      },
      {
        "event_id":"evt_smoke_after_001",
        "schema_version":"v1",
        "type":"after_tool_call",
        "session_id":"sess_smoke",
        "run_id":"run_smoke",
        "trace_id":"trace_smoke",
        "timestamp":"2026-06-22T10:00:02Z",
        "payload":{
          "tool_call_id":"call_smoke_001",
          "success":true,
          "result_preview":"# TraceShield",
          "result_size":13
        }
      }
    ]
  }'
```

期望：

```json
{
  "success": true,
  "accepted": 2,
  "duplicated": 0,
  "failed": 0
}
```

## 插件联调测试

启动真实 Core，然后运行插件 demo，使插件异步 flush 到真实 Core。

验证数据库：

```bash
sqlite3 core/app/data/traceshield.db "select event_type, count(*) from trace_events group by event_type;"
sqlite3 core/app/data/traceshield.db "select id, success, result_preview from tool_results order by created_at desc limit 5;"
```

## 验收标准

```text
1. 插件异步事件不会丢。
2. 重复上传不会重复入库。
3. before_tool_call 和 after_tool_call 可以形成工具调用链。
4. 数据库可查 trace_events 和 tool_results。
5. 测试通过。
```

## Codex 执行指令

```text
请执行第 4 轮：实现 /v1/events/batch 异步事件入库。
要求支持 event_id 幂等去重，保存 trace_events，并把 before_tool_call/after_tool_call 投影到 tool_calls/tool_results。
补充 pytest，覆盖重复事件、工具调用、工具结果和 agent_end。
运行 curl smoke 和插件联调，确认真实插件事件能进入数据库。
```

---

# 第 5 轮：实现仪表盘 API，对接前端首页

## 目标

让前端首页仪表盘不再使用 toy data，而是读取 Core 数据库。

## 任务

实现：

```http
GET /api/module4/dashboard?time_range=7d
```

返回结构必须适配现有前端。

## 返回结构

```json
{
  "success": true,
  "data": {
    "summary": {
      "total_alerts": 12,
      "critical_count": 3,
      "high_risk_count": 5,
      "query_count": 7,
      "start_time": "2026-06-15T00:00:00Z",
      "latest_report_id": "report_xxx"
    },
    "risk_trend": [
      {"bucket": "2026-06-22", "alert_count": 4}
    ],
    "channels": [
      {"channel": "chrome.exe", "alert_count": 4, "percent": 33.3}
    ],
    "top_departments": [
      {"department_name": "研发部", "alert_count": 5, "high_risk_count": 2, "critical_count": 1, "risk_score_avg": 86.2}
    ],
    "top_users": [
      {"username": "amy.sales", "department_name": "销售部", "alert_count": 3, "risk_score_avg": 91.5}
    ],
    "high_risk_events": [
      {
        "event_id": "evt_xxx",
        "risk_level": "critical",
        "username": "amy.sales",
        "department_name": "销售部",
        "file_name": "客户资料.xlsx",
        "timestamp": "2026-06-22T10:00:00Z"
      }
    ]
  }
}
```

## time_range 支持

必须支持：

```text
today
7d
30d
this_month
```

## 测试

```bash
cd core
pytest -q tests/test_dashboard_api.py
```

测试内容：

```text
1. 空数据库时 dashboard 返回 success=true，数组为空，不报错。
2. 插入 3 条 security_events 后 total_alerts=3。
3. critical_count 统计正确。
4. high_risk_count 统计正确。
5. risk_trend 按天聚合正确。
6. top_departments 聚合正确。
7. top_users 聚合正确。
8. high_risk_events 只返回 high/critical。
9. today/7d/30d/this_month 时间过滤正确。
```

## 前端联调测试

1. 把用户提供的 `index.html` 放到：

```text
core/app/static/index.html
```

2. 在 FastAPI 挂载静态页面：

```http
GET /
```

返回该 HTML。

3. 启动 Core：

```bash
cd core
uvicorn app.main:app --reload --port 8000
```

4. 浏览器打开：

```text
http://127.0.0.1:8000/
```

5. 检查：

```text
顶部 Database OK
仪表盘能加载
风险趋势不报错
最新高危事件表不报错
```

## 插件联调测试

先用插件触发几次危险工具调用，再刷新仪表盘。

```text
cat .env       → 生成 critical 事件
rm -rf /tmp/x  → 生成 critical 事件
external-upload.com → 生成 high 事件
```

然后打开仪表盘，确认总告警数量增加。

## 验收标准

```text
1. /api/module4/dashboard 返回前端可渲染结构。
2. 空数据库不崩。
3. 有事件时统计正确。
4. 真实插件触发 BLOCK 后，仪表盘总告警增加。
5. 前端首页能打开。
```

## Codex 执行指令

```text
请执行第 5 轮：实现 /api/module4/dashboard 仪表盘 API，并适配现有 index.html。
需要从 security_events、chat_messages、reports 聚合数据。
支持 today/7d/30d/this_month。
将 index.html 挂载到 GET /，并补充 dashboard API 测试。
完成后通过插件触发危险工具调用，刷新前端确认仪表盘数据变化。
```

---

# 第 6 轮：实现事件详情 API，对接右侧洞察面板

## 目标

点击前端右侧或仪表盘里的事件 ID，可以看到完整事件详情。

## 任务

实现：

```http
GET /api/module4/events/{event_id}
```

## 返回结构

```json
{
  "success": true,
  "event": {
    "event_id": "evt_xxx",
    "risk_level": "critical",
    "risk_score": 95.0,
    "event_status": "open",
    "timestamp": "2026-06-22T10:00:00Z",
    "username": "amy.sales",
    "user_id": "u001",
    "department_name": "销售部",
    "department_id": "d001",
    "host_name": "host-001",
    "host_id": "h001",
    "ip_address": "192.168.1.10",
    "file_name": ".env",
    "file_path": "/workspace/project/.env",
    "sensitive_type": "credential",
    "sensitive_level": "S4",
    "operation": "read",
    "process_name": "openclaw",
    "target": "local_file",
    "target_type": "file"
  },
  "risk_explanation": "工具调用尝试读取敏感环境变量文件，可能导致凭据泄露。",
  "recommended_actions": [
    "保持阻断结果",
    "检查用户任务是否确实需要访问敏感文件",
    "将 .env 加入禁止读取策略"
  ],
  "tool_call": {},
  "audit_decision": {},
  "evidence": [],
  "risk_graph": []
}
```

## 测试

```bash
cd core
pytest -q tests/test_event_detail_api.py
```

测试内容：

```text
1. 查询存在的事件返回 success=true。
2. 查询不存在的事件返回 success=false 或 404，前端不崩。
3. 返回字段包含前端 renderEventDetailPanel 需要的字段。
4. event_id、risk_level、risk_score、event_status、timestamp 必须存在。
5. recommended_actions 必须是数组。
6. tool_call 和 audit_decision 能关联返回。
```

## 前端联调测试

1. 通过插件触发 `cat .env`。
2. 打开仪表盘。
3. 点击最新高危事件的“详情”。
4. 右侧面板必须显示：

```text
事件摘要
风险解释
用户与终端
文件与外发
处置建议
```

## 验收标准

```text
1. 事件详情 API 可用。
2. 前端点击事件 ID 能正常打开右侧详情。
3. 详情中能看到工具调用和审计结果。
4. 查询不存在事件不会导致前端崩溃。
```

## Codex 执行指令

```text
请执行第 6 轮：实现 /api/module4/events/{event_id}。
该接口必须适配 index.html 右侧洞察面板需要的字段。
从 security_events、tool_calls、audit_decisions 中关联查询。
补充 pytest，并用前端点击事件详情完成联调。
```

---

# 第 7 轮：实现会话 API，支撑左侧会话和中间聊天

## 目标

让左侧会话列表和中间聊天区域可用。

## 任务

实现：

```http
GET    /sessions
POST   /sessions
DELETE /sessions/{session_id}
GET    /sessions/{session_id}/render
POST   /sessions/{session_id}/chat
POST   /sessions/{session_id}/abort
POST   /sessions/{session_id}/approve
```

第一版不要求接真实大模型，`/chat` 可以先用规则生成分析回答，但必须使用 SSE 形式返回，适配现有前端。

## /sessions 返回

```json
[
  {
    "id": "sess_xxx",
    "title": "最近 7 天有哪些高风险事件",
    "created_at": "2026-06-22T10:00:00Z",
    "updated_at": "2026-06-22T10:10:00Z"
  }
]
```

## /sessions POST 返回

```json
{
  "id": "sess_xxx"
}
```

## /sessions/{id}/chat 行为

请求：

```json
{
  "message": "最近 7 天有哪些高风险事件？"
}
```

行为：

```text
1. 保存 user 消息到 chat_messages。
2. 根据问题简单判断要查询 dashboard 还是 event detail。
3. 生成 assistant 分析。
4. 保存 assistant 消息。
5. 用 SSE 返回 A2UI-like 消息。
```

第一版可以简化，不需要完整 A2UI SDK，但必须让现有前端能显示内容。

## SSE 最小返回

前端的 `consumeSSEStream` 读取格式是：

```text
data: {json}\n\n
```

可以发送：

```json
{
  "beginRendering": {
    "root": "root"
  }
}
```

然后发送 surfaceUpdate，生成 Column/Card/Text。为了简单，Codex 可以参考前端 `processA2UIMessage` 和 `renderComponent` 支持的结构。

## /render 行为

返回历史消息的 SSE 文本或 JSON lines，使前端重新打开会话时能渲染。

## 测试

```bash
cd core
pytest -q tests/test_sessions_api.py
```

测试内容：

```text
1. POST /sessions 能创建会话。
2. GET /sessions 能列出会话。
3. DELETE /sessions/{id} 能软删除。
4. POST /sessions/{id}/chat 能保存 user 消息。
5. POST /sessions/{id}/chat 能保存 assistant 消息。
6. chat 返回 text/event-stream 或可被前端消费的流。
7. GET /sessions/{id}/render 能返回历史渲染内容。
```

## 前端联调测试

1. 打开 `http://127.0.0.1:8000/`。
2. 点击“新建会话”。
3. 输入：

```text
最近 7 天有哪些高风险事件？
```

4. 中间区域必须出现回答。
5. 左侧必须出现会话。
6. 刷新页面后，会话仍然存在。

## 插件联调测试

1. 先通过插件触发 2-3 条安全事件。
2. 再在前端问：

```text
最近 7 天有哪些高风险事件？
```

3. 回答中必须提到真实事件 ID。
4. 点击回答中的事件 ID，右侧可以打开详情。

## 验收标准

```text
1. 左侧会话可创建、展示、删除。
2. 中间聊天可发送、可显示回答。
3. 回答能引用真实 security_events。
4. 引用事件 ID 后右侧详情可打开。
5. 测试通过。
```

## Codex 执行指令

```text
请执行第 7 轮：实现 /sessions 系列接口，使现有三栏式前端可用。
第一版不用接真实大模型，但 /chat 必须根据数据库内容生成中文分析回答，并通过 SSE 返回前端可渲染的 A2UI-like 消息。
回答中出现的事件 ID 必须能被前端识别并点击查看详情。
补充 pytest，并完成前端手工联调。
```

---

# 第 8 轮：实现报告导出

## 目标

让“导出最新报告”和聊天里的报告下载链接可用。

## 任务

新增表：

```text
reports
```

实现：

```http
POST /api/module4/reports
GET  /api/module4/exports/{filename}
```

并让 `/sessions/{id}/chat` 在用户要求“生成报告”时调用报告逻辑。

## reports 表

```sql
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    title TEXT NOT NULL,
    report_type TEXT NOT NULL,
    time_range TEXT,
    content_markdown TEXT,
    content_html_path TEXT,
    content_pdf_path TEXT,
    generated_by TEXT DEFAULT 'eino-agent',
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);
```

## 报告内容

第一版只要求 HTML，内容包括：

```text
1. 报告标题
2. 时间范围
3. 总告警数
4. 高危/critical 数
5. Top 部门
6. Top 用户
7. 最新高危事件列表
8. 建议措施
```

## 导出路径

文件保存到：

```text
core/app/data/exports/report_xxx.html
```

数据库保存相对路径。

## 测试

```bash
cd core
pytest -q tests/test_reports_api.py
```

测试内容：

```text
1. POST /api/module4/reports 能生成 report。
2. reports 表有记录。
3. HTML 文件存在。
4. GET /api/module4/exports/{filename} 能下载。
5. 聊天请求“生成报告”时，回答中出现下载链接。
```

## 前端联调测试

1. 点击右侧“生成并导出周报”。
2. 中间回答里出现下载链接。
3. 右侧“下载链接”显示下载按钮。
4. 点击后能打开 HTML 报告。

## 插件联调测试

1. 通过插件触发若干真实事件。
2. 生成报告。
3. 报告中必须包含这些真实事件。

## 验收标准

```text
1. 报告能生成。
2. 报告能下载。
3. 报告数据来自数据库，不是固定假数据。
4. 前端下载按钮可用。
```

## Codex 执行指令

```text
请执行第 8 轮：实现报告生成和导出。
新增 reports 表，实现 POST /api/module4/reports 和 GET /api/module4/exports/{filename}。
当用户在 /sessions/{id}/chat 中请求生成报告时，生成 HTML 报告并在回答中返回 /api/module4/exports/... 下载链接。
补充测试，并通过前端按钮完成联调。
```

---

# 第 9 轮：补充风险证据和风险链路

## 目标

让右侧详情不只是“结论”，还能展示证据和风险传播链路。

## 任务

新增表：

```text
risk_evidence
risk_graph_edges
```

更新：

```text
/v1/audit/tool-call
/api/module4/events/{event_id}
```

## risk_evidence 表

```sql
CREATE TABLE IF NOT EXISTS risk_evidence (
    id TEXT PRIMARY KEY,
    audit_decision_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    evidence_key TEXT,
    evidence_value TEXT,
    evidence_hash TEXT,
    description TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (audit_decision_id) REFERENCES audit_decisions(id),
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id)
);
```

## risk_graph_edges 表

```sql
CREATE TABLE IF NOT EXISTS risk_graph_edges (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_call_id TEXT,
    source_node TEXT NOT NULL,
    target_node TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    evidence_id TEXT,
    confidence REAL DEFAULT 1.0,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (run_id) REFERENCES openclaw_runs(id),
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id)
);
```

## 最小风险链路

对于 `cat .env`：

```text
user_goal → command_param → exec_tool → sensitive_file
```

对于 `external-upload.com`：

```text
user_goal → url_param → network_tool → external_sink
```

对于 `rm -rf`：

```text
user_goal → command_param → exec_tool → destructive_action
```

## 测试

```bash
cd core
pytest -q tests/test_event_detail_api.py tests/test_audit_api.py
```

新增测试：

```text
1. BLOCK .env 会生成 risk_evidence。
2. BLOCK .env 会生成至少 3 条 risk_graph_edges。
3. /api/module4/events/{id} 返回 evidence 数组。
4. /api/module4/events/{id} 返回 risk_graph 数组。
```

## 前端联调测试

右侧详情可以先不画图，但 JSON 必须返回。可以先在详情面板文字里加入风险链路摘要。

## 插件联调测试

插件触发 `cat .env` 后，查询事件详情，必须能看到 evidence 和 risk_graph。

## 验收标准

```text
1. 审计不只是返回 reason，还保存证据。
2. 风险链路可以查询。
3. 事件详情 API 返回 evidence 和 risk_graph。
4. 测试通过。
```

## Codex 执行指令

```text
请执行第 9 轮：为审计结果补充风险证据和风险链路。
新增 risk_evidence 和 risk_graph_edges 表。
在 /v1/audit/tool-call 中为 BLOCK/ASK/WARN 生成证据和最小风险链路。
更新 /api/module4/events/{event_id} 返回 evidence 和 risk_graph。
补充测试，并用插件触发 cat .env 完成联调。
```

---

# 第 10 轮：实现策略表和自然语言策略入口的基础能力

## 目标

为后续 Eino 的 policy-management skill 做准备。

## 任务

新增表：

```text
policies
```

实现接口：

```http
GET  /api/module4/policies
POST /api/module4/policies
PATCH /api/module4/policies/{policy_id}
```

同时让规则引擎读取 policies。

## policies 表

```sql
CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    target TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    action TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## 第一版 policy 支持

只支持简单条件：

```json
{
  "field": "path",
  "operator": "contains",
  "value": ".env"
}
```

或者：

```json
{
  "field": "url",
  "operator": "contains",
  "value": "external-upload.com"
}
```

## 测试

```bash
cd core
pytest -q tests/test_policies_api.py tests/test_audit_api.py
```

测试内容：

```text
1. 能创建 policy。
2. disabled policy 不生效。
3. priority 高的 policy 先匹配。
4. policy action=BLOCK 时审计返回 BLOCK。
5. policy action=ASK 时审计返回 ASK。
```

## 插件联调测试

1. 创建策略：禁止访问 `secret.txt`。
2. 插件调用读取 `secret.txt`。
3. Core 返回 BLOCK。
4. 插件阻断。
5. 仪表盘新增事件。

## 验收标准

```text
1. 策略可以创建、查询、关闭。
2. 规则引擎会读取策略。
3. 插件能被新策略影响。
4. 测试通过。
```

## Codex 执行指令

```text
请执行第 10 轮：实现 policies 表和基础策略接口。
规则引擎需要先读取 enabled policies，再执行内置规则。
第一版只支持 contains 条件和 ALLOW/WARN/ASK/BLOCK 动作。
补充测试，并通过插件读取 secret.txt 验证新策略能够阻断。
```

---

# 第 11 轮：实现审批表和 ASK 闭环

## 目标

当 Core 返回 ASK 时，系统能记录审批请求，并让前端可以批准或拒绝。

## 任务

新增表：

```text
approvals
```

实现：

```http
POST /sessions/{session_id}/approve
```

注意：现有前端已经有 approve 逻辑，会向这个接口发送：

```json
{
  "approved": true,
  "reason": ""
}
```

## approvals 表

```sql
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    tool_call_id TEXT NOT NULL,
    audit_decision_id TEXT,
    status TEXT NOT NULL,
    reason TEXT,
    requested_at DATETIME NOT NULL,
    resolved_at DATETIME,
    approved_by TEXT,
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id),
    FOREIGN KEY (audit_decision_id) REFERENCES audit_decisions(id)
);
```

## 行为

```text
1. /v1/audit/tool-call 返回 ASK 时创建 approvals，status=pending。
2. /sessions/{session_id}/approve approved=true 时，更新最近 pending approval 为 approved。
3. approved=false 时，更新为 rejected。
4. 同时向 chat_messages 写入审批结果。
```

## 测试

```bash
cd core
pytest -q tests/test_approvals_api.py
```

测试内容：

```text
1. external-upload.com 返回 ASK。
2. ASK 生成 pending approval。
3. approve true 后状态变 approved。
4. approve false 后状态变 rejected。
5. 不存在 pending approval 时返回合理错误。
```

## 插件联调测试

1. 插件触发 external-upload.com。
2. Core 返回 ASK。
3. 插件进入 approval required。
4. 前端点击 Approve 或 Reject。
5. 数据库 approvals 状态更新。

## 验收标准

```text
1. ASK 不再只是返回给插件，还能落库。
2. 前端审批接口可用。
3. approvals 状态正确流转。
4. 测试通过。
```

## Codex 执行指令

```text
请执行第 11 轮：实现 approvals 表和 ASK 审批闭环。
当 /v1/audit/tool-call 返回 ASK 时创建 pending approval。
实现 /sessions/{session_id}/approve，更新审批状态并写入聊天消息。
补充测试，并用插件触发 external-upload.com 完成联调。
```

---

# 第 12 轮：上传文档接口与会话附件

## 目标

让前端“上传文档”功能不报错，并把上传文件关联到会话。

## 任务

新增表：

```text
uploaded_documents
```

实现：

```http
POST /sessions/{session_id}/docs
```

## uploaded_documents 表

```sql
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER,
    parsed_text_preview TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);
```

## 文件保存

保存到：

```text
core/app/data/uploads/{session_id}/{safe_filename}
```

必须做：

```text
1. 文件名安全处理。
2. 文件大小限制，默认 10MB。
3. 计算 sha256。
4. 只保存 preview，不强行解析复杂格式。
```

## 测试

```bash
cd core
pytest -q tests/test_upload_docs_api.py
```

测试内容：

```text
1. 上传 txt 成功。
2. uploaded_documents 有记录。
3. 文件实际存在。
4. 超过大小限制返回错误。
5. 非法 session 返回错误。
```

## 前端联调测试

1. 新建会话。
2. 上传一个 txt 文件。
3. 前端显示 uploaded。
4. 数据库中有 uploaded_documents 记录。

## 验收标准

```text
1. 上传接口可用。
2. 文件不会乱放。
3. 数据库能关联 session。
4. 测试通过。
```

## Codex 执行指令

```text
请执行第 12 轮：实现 /sessions/{session_id}/docs 上传文档接口。
新增 uploaded_documents 表，保存文件路径、hash、大小、preview。
限制文件大小并处理安全文件名。
补充测试，并用前端上传文件完成联调。
```

---

# 第 13 轮：接入实验代码中的规则/风险模型，替换简单规则

## 目标

把之前实验代码里的边界分析、tool_mapper、risk_graph 等核心逻辑逐步接入 Core，但不能破坏已有插件协议。

## 任务

1. 阅读实验代码中的核心模块。
2. 只抽取纯逻辑，不搬 runner/evaluator/实验数据。
3. 在 `services/audit_engine.py` 中封装统一接口。
4. 保持 `/v1/audit/tool-call` 请求和响应不变。
5. 用实验逻辑增强风险判断和证据生成。

## 禁止

```text
1. 不要把实验数据集全部塞进 Core。
2. 不要让 Core 启动依赖实验 runner。
3. 不要改变插件协议。
4. 不要为了接实验代码破坏已有测试。
```

## 推荐封装

```python
class AuditEngine:
    def audit_tool_call(self, request: AuditToolCallRequest) -> AuditDecisionResponse:
        ...
```

内部可以调用：

```text
boundary model
rule engine
tool mapper
risk graph builder
```

## 测试

```bash
cd core
pytest -q
```

新增测试：

```text
1. 实验模型能识别 source → sink。
2. 敏感文件读取生成 sensitive_path evidence。
3. 外部 URL 生成 external_sink evidence。
4. 危险命令生成 dangerous_command evidence。
5. 原有第 3 轮 API 测试全部继续通过。
```

## 插件联调测试

用插件真实请求验证：

```text
cat .env
cat ~/.ssh/id_rsa
curl https://external-upload.com/drop
rm -rf /tmp/x
read README.md
```

## 验收标准

```text
1. 实验代码逻辑被 Core 使用。
2. 插件协议不变。
3. 旧测试不破。
4. 风险证据更丰富。
5. 前端事件详情能看到更好的解释。
```

## Codex 执行指令

```text
请执行第 13 轮：在不破坏现有 Core API 的前提下，接入实验代码中的核心审计逻辑。
只抽取 boundary、tool_mapper、risk_graph 等纯逻辑，不搬实验数据和 runner。
封装 AuditEngine，保持 /v1/audit/tool-call 请求响应不变。
所有旧测试必须继续通过，并补充实验逻辑相关测试。
最后用插件真实请求完成联调。
```

---

# 第 14 轮：端到端演示脚本和验收报告

## 目标

形成可答辩、可复现、可交付的端到端演示。

## 任务

创建：

```text
core/scripts/e2e_demo.sh
core/docs/e2e_demo.md
core/docs/test_report.md
```

## e2e_demo.sh 内容

脚本需要自动完成：

```text
1. 重置数据库。
2. 启动 Core 或提示用户启动。
3. 发送 ALLOW 请求。
4. 发送 BLOCK 请求。
5. 发送 ASK 请求。
6. 批量上传插件事件。
7. 查询 dashboard。
8. 查询 event detail。
9. 创建 session。
10. 发送 chat。
11. 生成 report。
12. 输出关键结果。
```

如果无法自动启动插件，也要提供插件联调步骤。

## 测试命令总汇

```bash
# Core
cd core
pytest -q

# Core 启动
uvicorn app.main:app --reload --port 8000

# 插件
cd openclaw-plugin
npm run typecheck
npm test
npm run build

# Smoke
cd core
bash scripts/smoke_plugin_core.sh
bash scripts/smoke_frontend_api.sh
bash scripts/e2e_demo.sh
```

## 验收场景

必须写入 `docs/test_report.md`：

```text
场景 1：读取 README.md
期望：ALLOW，数据库保存 tool_call，无 security_event 或 low event。

场景 2：读取 .env
期望：BLOCK，插件阻断，数据库保存 critical security_event，前端仪表盘增加。

场景 3：rm -rf
期望：BLOCK，插件阻断，风险解释为危险命令。

场景 4：访问 external-upload.com
期望：ASK，approval pending，前端可审批。

场景 5：上传 after_tool_call 事件
期望：trace_events 和 tool_results 有记录。

场景 6：前端问最近 7 天高危事件
期望：中间回答引用真实事件 ID，右侧可打开详情。

场景 7：导出报告
期望：生成 HTML 文件并可下载。
```

## 验收标准

```text
1. 一键测试文档完整。
2. e2e demo 可复现。
3. Core、插件、前端都被覆盖。
4. 有测试报告。
5. 可以作为答辩演示脚本。
```

## Codex 执行指令

```text
请执行第 14 轮：补充端到端演示脚本和测试报告。
创建 scripts/e2e_demo.sh、docs/e2e_demo.md、docs/test_report.md。
演示必须覆盖 ALLOW、BLOCK、ASK、事件入库、仪表盘、事件详情、聊天分析和报告导出。
运行全部 pytest 和插件测试，记录结果。
```

---

## 7. 最终验收清单

项目完成后，必须满足：

```text
[ ] core pytest 全部通过
[ ] openclaw-plugin typecheck 通过
[ ] openclaw-plugin test 通过
[ ] openclaw-plugin build 通过
[ ] /api/module4/health 返回 Database OK
[ ] /v1/audit/tool-call 能返回 ALLOW
[ ] /v1/audit/tool-call 能返回 BLOCK
[ ] /v1/audit/tool-call 能返回 ASK
[ ] /v1/events/batch 能入库
[ ] trace_events 有真实插件事件
[ ] tool_calls 有真实工具调用
[ ] audit_decisions 有真实审计结果
[ ] security_events 有真实高危事件
[ ] /api/module4/dashboard 能返回真实统计
[ ] /api/module4/events/{id} 能返回详情
[ ] /sessions 能创建和列出会话
[ ] /sessions/{id}/chat 能返回中文分析
[ ] 回答中的事件 ID 能点击打开右侧详情
[ ] 报告能生成和下载
[ ] Core 关闭 mock-core 后，插件仍可联调真实 Core
```

---

## 8. 推荐提交节奏

每一轮单独提交：

```bash
git checkout -b core-round-0
# 完成第 0 轮
git add .
git commit -m "core: add FastAPI baseline and health check"

# 合并后继续下一轮
```

如果你们不想每轮开分支，至少每轮一个 commit：

```text
core: add db models and health check
core: add plugin protocol schemas
core: implement audit tool-call api
core: implement event batch ingest
core: implement dashboard api
core: implement event detail api
core: implement session chat api
core: implement report export
core: add risk evidence and graph
core: add policies
core: add approvals
core: add upload docs
core: integrate experiment audit engine
core: add e2e demo and test report
```

---

## 9. 给 Codex 的总启动指令

可以直接复制下面这一段给 Codex：

```text
你现在负责开发 TraceShield Core。
请严格按 docs/TraceShield_Core与前端数据库联动执行任务书.md 执行。
不要一次完成所有轮次。每次只执行一轮。
每轮完成后必须：
1. 列出修改文件；
2. 列出新增测试；
3. 运行 core pytest；
4. 运行 openclaw-plugin 的 typecheck/test/build；
5. 如果本轮涉及插件接口，必须运行插件到 Core 的联调；
6. 如果本轮涉及前端接口，必须用现有 index.html 进行接口联调；
7. 输出失败项和下一步建议。

禁止事项：
1. 不要破坏插件已有协议；
2. 不要删除 mock-core；
3. 不要把实验数据集全部塞进 Core；
4. 不要保存完整敏感原文；
5. 不要用固定假数据冒充数据库数据；
6. 不要跳过测试。

现在先执行第 0 轮。
```

---

## 10. 当前最推荐你先做哪几轮

不要一口气做完 14 轮。现在最应该先完成：

```text
第 0 轮：Core 基线
第 1 轮：数据库 8 张表
第 2 轮：插件协议 Schema
第 3 轮：真实 /v1/audit/tool-call
第 4 轮：真实 /v1/events/batch
第 5 轮：仪表盘 API
第 6 轮：事件详情 API
第 7 轮：会话 API
```

做到第 7 轮，你的系统就已经有完整闭环：

```text
插件拦截 → Core 审计 → 数据库入库 → 仪表盘展示 → 事件详情 → 聊天分析
```

后面的报告、策略、审批、实验代码增强，可以作为第二阶段继续做。

