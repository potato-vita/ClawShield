# TraceShield Frontend Codex Progress

> 按用户要求，前端多轮执行记录放在 `doc/frontend-codex/`。后续 Round 1-8 将追加到本文件，不覆盖前轮内容。

## Round 0 - Repository Check

### Goal

- 检查 TraceShield 仓库是否具备前端开发所需的项目上下文。
- 记录当前分支、目录概要和 Node.js/npm 版本。
- 仅创建执行记录，不创建 `web/`，不修改业务代码。

### Repository Snapshot

- 当前分支：`feat/core-postgresql`
- Node.js：`v24.14.1`
- npm：`11.11.0`
- `core/`：存在
- `openclaw-plugin/`：存在
- `mock-core/`：存在
- `doc/`：存在
- `docs/`：不存在
- `web/`：未创建

### Main Directories

```text
.
├── core/
├── doc/
│   └── frontend-codex/
├── mock-core/
└── openclaw-plugin/
```

### Files Added

- `doc/frontend-codex/frontend-codex-progress.md`

### Files Changed

- 无。

### Commands Run

```bash
git branch --show-current
node -v
npm -v
ls -la
test -d openclaw-plugin
test -d core || echo "core may not exist yet"
test -d mock-core
test -d docs
test -d doc
test -d web
```

### Result

- Success。前端开发依赖的仓库上下文已确认。
- Round 0 未创建 `web/`，未修改 Core、OpenClaw 插件或 Mock Core。
- 执行前已存在的未跟踪文件 `STARTUP.md`、`TraceShield_前端_Codex_多轮执行方案.md`、`teset、` 未被修改。

### Verification

- [x] 当前分支已记录
- [x] Node.js 和 npm 版本已记录
- [x] `core/` 存在
- [x] `openclaw-plugin/` 存在
- [x] `mock-core/` 存在
- [x] 独立前端记录目录已创建
- [x] 无业务代码变更

### Notes

- 方案原建议记录路径为 `docs/frontend-codex-progress.md`。本次按用户明确要求，适配为 `doc/frontend-codex/frontend-codex-progress.md`。
- 当前系统没有 Docker；Round 0 不需要启动 Core 或数据库。后续 API 联调轮次将优先验证 mock fallback，并如实记录 Core 运行状态。

### Next Round

- Round 1：创建 Vue 3 + Vite + TypeScript 的 `web/` 项目骨架。

## Round 1 - Web Project Skeleton

### Goal

- 创建 Vue 3 + Vite + TypeScript 前端工程。
- 配置 Tailwind CSS、Vue Router、Pinia 和基础路由页面。

### Files Added

- `web/package.json`、`web/package-lock.json`
- `web/tsconfig.json`、`web/tsconfig.app.json`、`web/tsconfig.node.json`
- `web/vite.config.ts`、`web/tailwind.config.js`、`web/postcss.config.js`
- `web/index.html`、`web/.env.example`
- `web/src/main.ts`、`web/src/App.vue`、`web/src/env.d.ts`
- `web/src/router/index.ts`
- `web/src/stores/runtimeStore.ts`
- `web/src/styles/tokens.css`、`web/src/styles/globals.css`
- `web/src/pages/RuntimeAudit.vue`、`ToolCalls.vue`、`PolicyCenter.vue`、`CoreStatus.vue`、`ComingSoon.vue`

### Commands Run

```bash
cd web && npm install
cd web && npm run typecheck
cd web && npm run build
cd web && npm run dev
curl http://127.0.0.1:5173/runtime
```

### Result

- Success。Vite `6.4.3` 生产构建成功，1588 modules transformed。
- 开发服务启动在 `127.0.0.1:5173`，`/runtime` 返回应用入口。
- npm audit 报告 0 vulnerabilities。
- npm 对方案指定的 `lucide-vue-next` 输出 deprecated 警告，但不影响安装、类型检查或构建。

### Verification

- [x] Vue 3 + Vite + TypeScript
- [x] Tailwind CSS
- [x] Vue Router 与指定路由
- [x] Pinia
- [x] Naive UI / Vue Flow / Lucide 依赖
- [x] TraceShield 色彩令牌
- [x] typecheck/build/dev

### Next Round

- Round 2：OpenClaw-like 审计工作台布局。

## Round 2 - Audit Workspace Layout

### Goal

- 完成 OpenClaw-like 实时审计工作台骨架。
- 补齐顶部状态、左侧导航/会话、右侧 Inspector 与底部 Evidence Path。

### Files Added

- `web/src/layouts/AuditWorkspaceLayout.vue`
- `web/src/components/nav/SideRail.vue`、`TopStatusBar.vue`
- `web/src/components/sessions/SessionPanel.vue`、`SessionCard.vue`
- `web/src/components/metrics/MetricCard.vue`
- `web/src/components/inspector/InspectorPanel.vue`、`DecisionTab.vue`、`EvidenceTab.vue`、`AssistantTab.vue`
- `web/src/components/evidence/EvidencePathTable.vue`

### Result

- Success。固定顶栏、窄导航、可折叠会话栏、380px Inspector 和默认展开的 Evidence Path 已实现。
- 浅色、细边框、金属灰与中国红点缀的工作台视觉已建立。
- `npm run typecheck` 与 `npm run build` 通过，Vite 生产构建完成 1619 modules transformed。

### Verification

- [x] 左侧窄导航与会话列表
- [x] 会话列表可折叠
- [x] 顶部 Core / PostgreSQL / Plugin 状态
- [x] Inspector 三个 Tab
- [x] Evidence Path 可折叠
- [x] typecheck/build

### Next Round

- Round 3：Runtime Audit 静态交互与多步攻击链。

## Round 3 - Runtime Audit Interaction

### Goal

- 使用 mock data 完成会话选择、多步风险路径、Inspector 与 Evidence Path 联动。

### Main Additions

- `src/mock/runtimeMock.ts` 与 session/toolCall/graph/evidence/policy 类型。
- `AuditPathCanvas` / `PathNode` / `PathLegend`。
- Path / Timeline / Tool Calls / Conversation 四个运行视图。
- `payroll-leak-demo` 高危链路：User Request → shell_exec → read_file → process_data → external_send → BLOCKED。

### Result

- Success。点击路径节点会同步更新 Inspector 和底部证据步骤高亮。
- Timeline 默认 Risk Only，Tool Calls 展示当前 run，Conversation 只展示脱敏摘要。
- BLOCK 节点使用中国红与轻量脉冲动效。
- `npm run typecheck` 与 `npm run build` 通过，1644 modules transformed。

### Verification

- [x] 至少 3 个审计会话
- [x] 多步攻击链可视化
- [x] 节点 / Inspector / Evidence 联动
- [x] 四个 Runtime Tab
- [x] typecheck/build

### Next Round

- Round 4：API Client、Core 数据接入与 mock fallback。

## Round 4 - Core API Client and Fallback

### Goal

- 接入 Core 真实数据，同时保留开发环境 mock fallback。

### Main Additions

- `src/api/client.ts` 统一 base URL、JSON、超时与错误处理。
- dashboard/sessions/runs/toolCalls/policies/coreStatus API 模块。
- Core `/v1/audit/events` 到前端 sessions/runs/tool calls 的映射。
- Core risk graph / evidence path 映射与非 demo 通用路径渲染。

### Compatibility

- 现有 Core 已实现 dashboard、audit events、run graph/evidence、tool-call decision 和 health。
- 方案中 sessions/runs 列表、policies REST 与 `/v1/core/status` 尚未在 Core 实现。前端从 audit events 派生 sessions/runs，policy 操作保留 API client 并优雅回退。

### Result

- Success。`VITE_USE_MOCK_DATA=true` 直接使用演示数据。
- `VITE_USE_MOCK_DATA=false` 时请求 Core；失败时显示错误条并保留 mock 工作台，不会白屏。
- 本轮 `npm run typecheck` 与 `npm run build` 通过，1649 modules transformed。

### Verification

- [x] API client 和环境变量
- [x] Core 已有接口的数据映射
- [x] mock / Core / fallback 三种数据源状态
- [x] 失败不白屏
- [x] typecheck/build

### Next Round

- Round 5：Tool Calls 与 Policy Center 产品页。

## Round 5 - Tool Calls and Policy Center

### Goal

- 将扩展路由建设为可使用的审计库存与策略管理页。

### Result

- Tool Calls 展示时间、会话/run、工具、资源、决策、风险、延迟与策略命中，支持 decision/risk/tool kind 与文本筛选。
- 点击 Tool Call 可回到 Runtime Audit 并定位对应会话、run 和节点。
- Policy Center 支持启停规则，以及通过四种中文模板新建规则，无需手写 JSON。
- 无后端时使用 mock 并显示操作反馈；Core 模式下策略接口不存在时显示明确提示。
- `npm run typecheck` 与 `npm run build` 通过，4427 modules transformed。

### Verification

- [x] Tool Calls 表格与筛选
- [x] Tool Call 回跳联动
- [x] Policy 启停
- [x] 模板化新建
- [x] 操作反馈与 mock fallback

### Next Round

- Round 6：Core 状态、Assistant 解释与产品成熟度。

## Round 6 - Product Maturity

### Result

- 顶部 Core / PostgreSQL / Plugin 状态可点击，弹层展示 Core、DB、Plugin、事件量、队列、Core 版本与策略版本。
- Assistant 根据当前节点、决策和风险链生成中文解释与建议，未接 Eino。
- Inspector 补齐 Keep Blocked / Approve Once / Create Policy / Add to Allowlist 预览操作与反馈。
- 补齐 Core Status 完整页、会话新事件闪烁、证据滚动高亮、状态呼吸灯与空状态。
- `npm run typecheck` 与 `npm run build` 通过，4429 modules transformed。

### Verification

- [x] Core 状态弹层与完整页
- [x] Assistant 规则解释
- [x] 四个 Inspector 操作反馈
- [x] 关键动效
- [x] 空状态与错误状态

### Next Round

- Round 7：SSE 实时审计事件流。

## Round 7 - SSE Realtime Stream

### Result

- 新增 `src/api/stream.ts`，通过 EventSource 接入 `/v1/stream/audit-events`。
- 处理 `connected`、`audit_event`、`trace_event`、`metric_update` 和可选 `heartbeat`。Core 当前的 heartbeat 为 SSE comment，连接 open 状态仍能正确保持。
- 断线显示 Realtime Offline，3 秒后自动重连，不向页面抛出未处理错误。
- audit event 增量更新会话排序、Tool Calls、指标和当前 Timeline；trace event 更新 Plugin Last Seen 与 Timeline。
- `npm run typecheck` 与 `npm run build` 通过，4431 modules transformed。

### Verification

- [x] SSE 客户端与事件分发
- [x] 顶部 Realtime 连接状态
- [x] 自动重连
- [x] 断线不白屏
- [x] 增量会话/指标/Timeline 更新

### Next Round

- Round 8：最终视觉、文档、smoke check 与演示验收。

## Round 8 - Final Polish and Acceptance

### Documentation Added

- `doc/frontend-codex/frontend-design.md`
- `doc/frontend-codex/frontend-api-map.md`
- `web/README.md`
- `web/scripts/smoke-check.mjs`

### Final Validation

```bash
cd web && npm run typecheck
cd web && npm run build
cd web && VITE_USE_MOCK_DATA=false npm run build
cd web && npm run dev
cd web && npm run smoke
```

### Result

- Success。所有 Round 0-8 已完成。
- 视觉系统已统一为浅色画布、白色面板、金属灰细边框、浅红渐变和中国红关键点缀。
- Runtime 固定栅宽和高度为 1366×768 优化，1680px 以上自动扩展会话与 Inspector，适配 1920×1080。
- mock 与 Core 两种环境变量构建均通过。
- Smoke check 通过 `/runtime`、`/tool-calls`、`/policies`、`/core` 四个路由，并校验演示攻击链。
- Vite 开发服务保持在 `127.0.0.1:5173`。

### Final Acceptance Checklist

- [x] `/runtime` 完整工作台
- [x] Session 搜索、筛选、切换与折叠
- [x] Path 节点可点击
- [x] Inspector 三个 Tab 及操作反馈
- [x] Evidence Path 联动高亮
- [x] Tool Calls 筛选与 Runtime 回跳
- [x] Policy Center 启停和模板新建
- [x] Core 状态弹层与详情页
- [x] mock fallback / Core API / SSE 接入能力
- [x] 错误、空状态和断线不破坏页面
- [x] 文档和 smoke check

### Environment Note

- 该轮最初以 mock 验收；后续已确认 PostgreSQL 实例正常，并完成 Core/SSE 真实模式端到端验收。Docker CLI 已安装，但当前登录会话无 Docker socket 权限。

## Post-delivery Live Integration Fix - 2026-07-01

- 更正旧的环境记录：Docker CLI 已安装但当前会话无 socket 权限；PostgreSQL 实例已在 5432 运行，`db:check` 通过。
- Core 新增 sessions、session runs 与 conversation summary 查询，纯对话会话不再依赖 tool call。
- SSE `trace_event` 携带脱敏 role/summary，前端可实时新增/置顶对话 Session 并更新 Conversation/Timeline。
- Core 补齐本地 Web 跨端口 HTTP/SSE 所需 CORS 头。
- `web/.env` 已切换 `VITE_USE_MOCK_DATA=false`，mock 状态不再伪装 Core Online。
- Core 与 Web 已由 `traceshield-core.service` / `traceshield-web.service` 持久托管并 enable。
- OpenClaw 离线队列由 58 条自动回灌到 0。
- 验收：Core health 200、CORS OPTIONS 204、SSE connected、sessions 4（包含 2 个 conversation-only sessions）、Web smoke 全通过。

## Navigation and Layout Refinement - 2026-07-01

- Runtime 与 Sessions 拆成 `/runtime` 和 `/sessions` 两个独立路由，Side Rail 使用 exact active 状态，不再同时高亮。
- 新增 Sessions 档案页：会话指标、搜索、风险筛选、conversation-only 统计与 Runtime 回跳。
- Runtime 内左侧栏改为 `Runtime context / Recent sessions`，与全局 Sessions 功能分工明确。
- 全局移除 CSS gradient，改用纯色画布、白色卡片、细边框与低强度阴影。
- 重排 Runtime 的 Rail / Context / Main / Inspector / Evidence 间距，增加卡片分隔和 cubic-bezier 过渡，并支持 `prefers-reduced-motion`。
