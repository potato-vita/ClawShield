# TraceShield 前端多轮 Codex 执行方案

> 目标：开发一个 **OpenClaw-like 的 TraceShield 实时审计控制台**。  
> 它不是传统安全大屏，也不是聊天界面，而是围绕 OpenClaw 会话展示工具调用路径、风险链路、审计决策、证据路径和 Assistant 解释。

---

## 0. 前端最终定位

产品名称：

```text
TraceShield 实时审计控制台 / Runtime Audit Console
```

核心表达：

```text
OpenClaw 原本展示 Agent 与用户的聊天记录；
TraceShield 展示这段会话背后的工具调用路径、风险链路和阻断证据。
```

第一版前端目标：

```text
1. 打开页面就是 Runtime Audit 工作台。
2. 左侧像 OpenClaw 一样有会话列表。
3. 中间默认展示工具调用路径 Path。
4. 右侧 Inspector 展示 Decision / Evidence / Assistant。
5. 底部展示 Evidence Path。
6. 支持 Core API 接入，也支持开发环境 mock data。
```

视觉风格：

```text
浅色 OpenClaw-like 工作台
中国红点缀
浅红渐变卡片
金属科技感
不要深色黑客风
不要大面积红色
不要太花
```

推荐技术栈：

```text
Vue 3
Vite
TypeScript
Tailwind CSS
Pinia
Vue Router
Vue Flow
Naive UI
```

---

## 1. 给 Codex 的通用规则

每一轮都要把下面这段作为前置要求发给 Codex：

```text
你正在开发 TraceShield 前端。

必须遵守：
1. 不要一次性完成所有功能，只完成当前轮次要求。
2. 每轮结束必须更新 docs/frontend-codex-progress.md。
3. 每轮必须记录：
   - 修改了哪些文件
   - 新增了哪些文件
   - 执行了哪些命令
   - 验证结果是否成功
   - 失败原因和修复方式
4. 每轮必须运行本轮指定验证命令。
5. 验证失败时不要假装成功，不要进入下一轮。
6. 不要破坏 openclaw-plugin 和 core 的现有代码。
7. 前端第一版必须支持 mock data，但不能在生产界面暴露 Demo Mode 按钮。
8. 页面必须围绕 session / run / tool call / decision / evidence 设计。
9. 视觉风格要符合：
   - 浅色
   - 中国红点缀
   - 金属科技感
   - OpenClaw-like 工作台
10. 不要做登录系统。
11. 不要接 Eino，先只做 Assistant 自动解释占位。
12. 不要把所有功能都做成 Coming Soon；Runtime Audit 必须真实可交互。
```

---

# Round 0：仓库检查与前端计划记录

## 目标

不写业务代码，只检查仓库，创建前端执行记录文件。

## 给 Codex 的提示词

```text
Round 0：请检查当前 TraceShield 仓库结构，为前端开发做准备。

任务：
1. 检查仓库根目录是否存在 openclaw-plugin、core、mock-core、docs。
2. 创建 docs/frontend-codex-progress.md。
3. 在 docs/frontend-codex-progress.md 记录：
   - 当前分支
   - 当前目录结构概要
   - Node 版本
   - npm 版本
   - 是否存在 core
   - 是否存在 openclaw-plugin
4. 不要创建 web 项目。
5. 不要修改已有业务代码。

验证命令：
- node -v
- npm -v
- ls
- test -d openclaw-plugin
- test -d core || echo "core may not exist yet"
- test -f docs/frontend-codex-progress.md

完成后停止，等待下一轮。
```

## 成功标准

```text
docs/frontend-codex-progress.md 存在
Round 0 有记录
没有修改业务代码
```

---

# Round 1：创建 web 前端项目骨架

## 目标

创建 Vue 3 + Vite + TypeScript 前端项目，搭好基础工程。

## 目录目标

```text
web/
├─ package.json
├─ vite.config.ts
├─ tsconfig.json
├─ index.html
├─ tailwind.config.js
├─ postcss.config.js
├─ src/
│  ├─ main.ts
│  ├─ App.vue
│  ├─ router/
│  │  └─ index.ts
│  ├─ stores/
│  │  └─ runtimeStore.ts
│  ├─ styles/
│  │  ├─ tokens.css
│  │  └─ globals.css
│  └─ pages/
│     ├─ RuntimeAudit.vue
│     ├─ ToolCalls.vue
│     ├─ PolicyCenter.vue
│     ├─ CoreStatus.vue
│     └─ ComingSoon.vue
```

## 依赖建议

```text
vue
@vitejs/plugin-vue
typescript
vue-router
pinia
tailwindcss
postcss
autoprefixer
naive-ui
@vue-flow/core
lucide-vue-next
```

## 给 Codex 的提示词

```text
Round 1：请创建 TraceShield 前端 web 项目骨架。

任务：
1. 在仓库根目录创建 web/。
2. 使用 Vue 3 + Vite + TypeScript。
3. 配置 Tailwind CSS。
4. 配置 Vue Router。
5. 配置 Pinia。
6. 安装 Naive UI、Vue Flow、lucide-vue-next。
7. 创建基础页面：
   - RuntimeAudit.vue
   - ToolCalls.vue
   - PolicyCenter.vue
   - CoreStatus.vue
   - ComingSoon.vue
8. 路由：
   - / 默认跳转 /runtime
   - /runtime
   - /tool-calls
   - /policies
   - /core
   - /assistant 使用 ComingSoon
   - /settings 使用 ComingSoon
9. 创建 styles/tokens.css，定义 TraceShield 色彩变量：
   - 中国红 #C91F37
   - 浅红背景 #FFF6F5
   - 页面背景 #F7F7F6
   - 金属灰 #CBD5E1
   - 科技蓝 #2563EB
10. App.vue 中渲染 router-view。
11. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm install
- cd web && npm run build
- cd web && npm run dev

完成后停止，等待下一轮。
```

## 成功标准

```text
web 项目可启动
npm run build 成功
/runtime 页面能打开
docs/frontend-codex-progress.md 记录 Round 1
```

---

# Round 2：实现 OpenClaw-like 工作台布局

## 目标

实现前端整体外壳，不接真实数据。

## 页面结构

```text
┌──────────────────────────────────────────────────────────────┐
│ TopStatusBar                                                  │
├──────┬────────────────────┬──────────────────────┬───────────┤
│ Rail │ SessionPanel       │ Main Runtime Area     │ Inspector │
├──────┴────────────────────┴──────────────────────┴───────────┤
│ EvidencePath                                                  │
└──────────────────────────────────────────────────────────────┘
```

## 需要新增组件

```text
src/layouts/AuditWorkspaceLayout.vue

src/components/nav/SideRail.vue
src/components/nav/TopStatusBar.vue

src/components/sessions/SessionPanel.vue
src/components/sessions/SessionCard.vue

src/components/metrics/MetricCard.vue

src/components/inspector/InspectorPanel.vue
src/components/inspector/DecisionTab.vue
src/components/inspector/EvidenceTab.vue
src/components/inspector/AssistantTab.vue

src/components/evidence/EvidencePathTable.vue
```

## 布局尺寸

```text
TopStatusBar: 56px
SideRail: 64px
SessionPanel: 280px，可折叠
InspectorPanel: 380px
EvidencePath: 240px，可折叠，默认展开
MainArea: 自适应
```

## 给 Codex 的提示词

```text
Round 2：请实现 TraceShield 的 OpenClaw-like 审计工作台布局。

任务：
1. 创建 AuditWorkspaceLayout.vue。
2. 实现 SideRail：
   - Logo
   - Runtime
   - Sessions
   - Tool Calls
   - Policies
   - Core
   - Assistant
   - Settings
3. 实现 TopStatusBar：
   - 标题：TraceShield 实时审计控制台 / Runtime Audit Console
   - 状态：Core Online、PostgreSQL Connected、OpenClaw Plugin Last Seen
   - 状态灯要有轻微呼吸效果
4. 实现 SessionPanel：
   - 可折叠
   - 顶部有 Risk / All 切换
   - 使用 mock session 数据
5. 实现 InspectorPanel：
   - Tabs: Decision / Evidence / Assistant
6. 实现 EvidencePathTable：
   - 默认展开
   - 支持折叠
   - 使用 mock evidence step 数据
7. RuntimeAudit.vue 使用该布局。
8. 不接后端 API。
9. 视觉风格：
   - 浅色背景
   - 白色卡片
   - 浅红渐变
   - 细边框
   - 中国红用于关键点缀
10. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

人工验证：
- 页面有左侧窄导航
- 页面有会话列表
- 页面有顶部状态栏
- 页面有右侧 Inspector
- 页面有底部 Evidence Path
- 整体不像普通后台表格，而像工作台

完成后停止，等待下一轮。
```

## 成功标准

```text
工作台布局完成
页面视觉接近 OpenClaw-like 产品
会话列表可折叠
Inspector 有三个 Tab
Evidence Path 可折叠
```

---

# Round 3：实现 Runtime Audit 静态交互

## 目标

用 mock data 完成核心页面交互：选择会话、展示 Path、点击节点、更新 Inspector 和 Evidence Path 高亮。

## 需要新增组件

```text
src/components/path/AuditPathCanvas.vue
src/components/path/PathNode.vue
src/components/path/PathLegend.vue

src/components/runtime/RuntimeTabs.vue
src/components/runtime/TimelinePanel.vue
src/components/runtime/ToolCallsPanel.vue
src/components/conversation/ConversationSummary.vue

src/mock/runtimeMock.ts
src/types/session.ts
src/types/toolCall.ts
src/types/graph.ts
src/types/evidence.ts
src/types/policy.ts
```

## Path 视觉结构

主链路 + 证据旁支：

```text
User Request
   ↓
shell_exec
   ↓
read_file payroll.xlsx  ← Sensitive Object
   ↓
process_data
   ↓
external_send suspicious-exfil.com ← Untrusted Sink
   ↓
BLOCKED by TraceShield
```

节点类型：

```text
user_intent
tool_call
sensitive_object
network_sink
policy_decision
blocked
```

## 给 Codex 的提示词

```text
Round 3：请实现 Runtime Audit 页面静态交互。

任务：
1. 创建 mock data：
   - 至少 3 个 audit sessions
   - 一个高危 demo session：payroll-leak-demo
   - 该 session 包含一个多步攻击 run：
     User Request → shell_exec → read_file → process_data → external_send → BLOCK
2. 实现 AuditPathCanvas：
   - 使用 Vue Flow 或自定义 SVG/HTML 均可
   - 展示主链路 + 证据旁支
   - BLOCK 节点使用中国红和轻微脉冲效果
3. 实现 Path 节点点击逻辑：
   - 点击工具节点 → Inspector 显示工具调用和决策
   - 点击敏感对象节点 → Inspector 显示证据
   - 点击 BLOCK 节点 → Inspector 显示阻断原因和命中策略
   - 点击 User Request → Inspector 显示 Conversation 摘要
4. 实现 RuntimeTabs：
   - Path
   - Timeline
   - Tool Calls
   - Conversation
   默认打开 Path。
5. Timeline 默认 Risk Only，可切换 All。
6. Tool Calls panel 显示当前 run 的工具调用表格。
7. ConversationSummary 使用聊天气泡样式，只展示摘要，不展示完整原文。
8. EvidencePathTable 支持当前 step 高亮。
9. 点击 Path 节点时，Evidence Path 对应 step 高亮。
10. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

人工验证：
- 选择 payroll-leak-demo 后，中间显示工具调用路径
- 点击 external_send，右侧显示 BLOCK 决策
- 点击 read_file，右侧显示敏感文件证据
- 点击 BLOCK 节点，底部 Evidence Path 高亮最后一步
- Timeline / Tool Calls / Conversation Tab 可切换

完成后停止，等待下一轮。
```

## 成功标准

```text
核心静态交互完整
路径图能表达多步攻击链
Inspector 会随点击更新
Evidence Path 有联动高亮
页面足够适合答辩展示
```

---

# Round 4：实现 API Client 与 Core 数据接入

## 目标

将 mock data 替换为 Core API 数据，同时保留开发环境 mock fallback。

## 需要新增 API 文件

```text
src/api/client.ts
src/api/dashboard.ts
src/api/sessions.ts
src/api/runs.ts
src/api/toolCalls.ts
src/api/policies.ts
src/api/coreStatus.ts
```

## 环境变量

```env
VITE_TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787
VITE_USE_MOCK_DATA=true
```

## 需要对接的 API

```http
GET /v1/dashboard/runtime-status
GET /v1/audit/sessions?filter=risk
GET /v1/audit/sessions/:sessionId/runs
GET /v1/runs/:runId/risk-graph
GET /v1/runs/:runId/evidence-path
GET /v1/tool-calls/:toolCallId/decision
GET /v1/tool-calls?session_id=xxx&decision=xxx&risk_level=xxx
GET /v1/policies
PATCH /v1/policies/:policyId
POST /v1/policies
GET /v1/core/status
```

如果 Core 暂时没有某些接口：

```text
前端 API client 必须优雅 fallback 到 mock data。
不要让页面白屏。
```

## 给 Codex 的提示词

```text
Round 4：请实现前端 API Client 和 Core 数据接入。

任务：
1. 创建 src/api/client.ts：
   - 从 VITE_TRACESHIELD_CORE_BASE_URL 读取 baseURL
   - 统一处理 JSON
   - 统一处理错误
2. 创建 dashboard/sessions/runs/toolCalls/policies/coreStatus API 文件。
3. 在 runtimeStore / sessionStore 中接入真实 API。
4. 支持 VITE_USE_MOCK_DATA=true 时使用 mock data。
5. 当 API 请求失败时：
   - 显示错误提示
   - 保留页面结构
   - fallback 到 mock data
6. 接入：
   - 顶部指标
   - 会话列表
   - 当前 session 的 runs
   - risk graph
   - evidence path
   - tool call decision
7. 页面中不要显示 Demo Mode 按钮。
8. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

验证场景：
1. VITE_USE_MOCK_DATA=true，页面使用 mock data。
2. VITE_USE_MOCK_DATA=false 且 Core 可用，页面使用 Core 数据。
3. VITE_USE_MOCK_DATA=false 且 Core 不可用，页面提示错误并 fallback。
4. 页面不白屏。

完成后停止，等待下一轮。
```

## 成功标准

```text
API client 完成
Core 可用时显示真实数据
Core 不可用时不崩溃
mock fallback 生效
```

---

# Round 5：Tool Calls 页面和 Policy Center 页面

## 目标

实现两个扩展页面，让系统更像成熟产品。

## Tool Calls 页面

字段：

```text
Time
Session
Run
Tool Name
Tool Kind
Resource
Decision
Risk Level
Latency
Policy Hits
```

筛选：

```text
decision
risk_level
tool_kind
```

## Policy Center 页面

展示：

```text
Policy Name
Rule ID
Severity
Action
Enabled
Hit Count
Last Hit Time
```

功能：

```text
1. 启用 / 禁用规则
2. 模板化新增规则
```

新增规则模板：

```text
禁止读取某类文件
禁止危险 shell 命令
外部网络请求需要审批
未知工具调用告警
```

## 给 Codex 的提示词

```text
Round 5：请实现 Tool Calls 页面和 Policy Center 页面。

任务：
1. ToolCalls.vue：
   - 表格展示工具调用
   - 支持 decision / risk_level / tool_kind 筛选
   - 点击行跳转或联动到 Runtime Audit 对应 tool call
2. PolicyCenter.vue：
   - 展示规则列表
   - 支持启用 / 禁用
   - 支持模板化新增规则
   - 不要求用户手写 JSON
3. 如果后端 API 不存在，使用 mock data。
4. 所有操作要有 Toast / Message 提示。
5. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

人工验证：
- Tool Calls 表格可筛选
- Policy Center 显示规则
- 可以启用 / 禁用规则
- 可以通过模板创建规则
- 无后端时 mock data 生效

完成后停止，等待下一轮。
```

## 成功标准

```text
Tool Calls 页面可用
Policy Center 页面可用
系统看起来不像单页 demo，而像真实产品
```

---

# Round 6：Core 状态弹层、Assistant 解释和成熟度补齐

## 目标

补齐产品感、解释能力和状态可见性。

## Core 状态弹层

点击顶部状态显示：

```text
Core Online
Database Connected
OpenClaw Plugin Last Seen
Events Ingested
Queue Size
Core Version
Policy Version
```

## Assistant 自动解释

第一版不接 Eino，只根据当前 decision / evidence / path 自动生成解释。

示例：

```text
本次调用被阻断，因为 Agent 在读取敏感文件后，尝试将处理结果发送到未信任外部域名。
风险链路为：read_file → process_data → external_send。
建议保持阻断，并检查用户输入中是否存在间接提示注入或越权任务指令。
```

## 动效

实现少量关键动效：

```text
1. 新事件进入时会话卡片轻微闪烁
2. BLOCK 节点红色轻微脉冲
3. Core 状态灯呼吸
4. Evidence Path 高亮滚动
5. 卡片 hover 有轻微金属浮起感
```

## 给 Codex 的提示词

```text
Round 6：请补齐前端成熟度。

任务：
1. 实现 Core 状态弹层。
2. AssistantTab 根据当前选中事件生成规则解释。
3. 实现关键动效：
   - BLOCK 节点脉冲
   - 状态灯呼吸
   - 会话卡片 hover
   - Evidence step 高亮
4. Inspector Actions 按钮：
   - Keep Blocked
   - Approve Once
   - Create Policy
   - Add to Allowlist
   第一版只做前端提示，不接真实审批接口。
5. 完善 Empty State 和 Error State。
6. 确保没有数据时页面不难看。
7. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

人工验证：
- 点击顶部状态能看到 Core 状态弹层
- Assistant 能解释当前 BLOCK 事件
- BLOCK 节点有轻微脉冲
- 页面无数据时有空状态
- 操作按钮有提示

完成后停止，等待下一轮。
```

## 成功标准

```text
页面已经有成熟产品感
Assistant 可解释当前事件
状态信息可查看
页面错误和空状态处理合理
```

---

# Round 7：SSE 实时事件流接入

## 目标

接入 Core 的实时事件流，让页面更像实时审计控制台。

## 接口

```http
GET /v1/stream/audit-events
```

事件类型：

```text
audit_event
trace_event
metric_update
heartbeat
```

处理：

```text
audit_event：更新会话列表、当前 Path、Inspector
metric_update：更新顶部指标卡片
trace_event：可选加入 Timeline
heartbeat：更新连接状态
```

## 给 Codex 的提示词

```text
Round 7：请接入 SSE 实时审计事件流。

任务：
1. 创建 src/api/stream.ts。
2. 使用 EventSource 连接 /v1/stream/audit-events。
3. 处理：
   - audit_event
   - trace_event
   - metric_update
   - heartbeat
4. 顶部显示 stream connected / disconnected。
5. 断开后自动重连。
6. 如果后端没有 SSE，页面不报错，只显示 Realtime Offline。
7. 收到新风险事件时：
   - 更新会话列表
   - 更新顶部指标
   - 如果是当前 session/run，更新 Timeline 或 Path
8. 更新 docs/frontend-codex-progress.md。

验证命令：
- cd web && npm run build
- cd web && npm run dev

人工验证：
- Core 有 SSE 时显示 Realtime Connected
- Core 无 SSE 时页面不崩溃
- 收到 metric_update 时顶部指标更新
- 收到 audit_event 时会话列表更新

完成后停止，等待下一轮。
```

## 成功标准

```text
SSE 可用
断线不崩
实时审计感明显增强
```

---

# Round 8：最终视觉打磨与演示验收

## 目标

完成答辩可用版本。

## 需要补充

```text
docs/frontend-design.md
docs/frontend-api-map.md
web/README.md
web/scripts/smoke-check.ts 或简单验证说明
```

## 最终验收流程

```text
1. 启动 Core
2. 启动前端
3. 打开 /runtime
4. 选择 payroll-leak-demo
5. 展示 Path
6. 点击 external_send
7. 右侧显示 BLOCK
8. 底部 Evidence Path 高亮
9. 打开 Assistant Tab
10. 解释风险链路
11. 打开 Tool Calls
12. 打开 Policies
13. 点击 Core 状态弹层
```

## 给 Codex 的提示词

```text
Round 8：请进行最终视觉打磨和演示验收。

任务：
1. 统一所有页面视觉：
   - 浅色
   - 中国红点缀
   - 细边框
   - 浅红渐变
   - 金属科技感
2. 修复明显布局问题。
3. 确保 1366x768 和 1920x1080 下都能正常展示。
4. 补充 docs/frontend-design.md。
5. 补充 docs/frontend-api-map.md。
6. 补充 web/README.md：
   - 如何启动
   - 如何使用 mock data
   - 如何连接 Core
7. 更新 docs/frontend-codex-progress.md。
8. 输出最终验收总结。

验证命令：
- cd web && npm run build
- cd web && npm run dev

最终人工验收：
- /runtime 主页面完整
- 会话列表可用
- Path 可点击
- Inspector 可切换
- Evidence Path 可高亮
- Tool Calls 可筛选
- Policy Center 可操作
- Core 状态弹层可打开
- 无数据和错误状态不丑
- 页面整体符合 TraceShield 视觉风格

完成后停止。
```

## 成功标准

```text
前端可用于比赛展示
视觉风格统一
主流程顺滑
文档完整
```

---

# 2. 不要让 Codex 做的事情

这次前端任务里不要让 Codex 做：

```text
1. 不要做登录系统。
2. 不要接 Eino。
3. 不要重写 Core。
4. 不要修改 openclaw-plugin 的接口契约。
5. 不要做 Run Demo Attack 前端按钮。
6. 不要大面积使用红色背景。
7. 不要做深色黑客风。
8. 不要把所有页面都做成空 Coming Soon。
9. 不要把聊天记录作为主视图。
10. 不要把工具调用路径做成普通日志列表。
```

---

# 3. 前端第一版必须有的能力

最后交付至少要做到：

```text
1. OpenClaw-like 左侧会话列表
2. 默认打开 Path 工具调用路径
3. 多步攻击链可视化
4. BLOCK 节点醒目但不刺眼
5. 右侧 Decision / Evidence / Assistant
6. 底部 Evidence Path
7. 顶部 Core / DB / Plugin 状态
8. Tool Calls 表格
9. Policy Center 简化规则管理
10. mock data fallback
11. Core API 接入能力
12. 可用于答辩演示
```

---

# 4. 建议执行节奏

不要一次性把 Round 0-8 全部丢给 Codex。

建议：

```text
先执行 Round 0
确认成功后执行 Round 1
Round 1 成功后执行 Round 2
每轮结束检查 docs/frontend-codex-progress.md
每轮都运行 build
每轮都打开页面人工看一眼
```

如果某一轮失败，不要继续下一轮，先修。

---

# 5. 答辩时的页面讲法

最终页面出来后，你可以这样讲：

```text
这是 TraceShield 实时审计控制台。我们借鉴了 OpenClaw 的工作台式交互，但没有重复展示聊天记录，而是把每个 OpenClaw 会话背后的工具调用路径抽象出来。

左侧是审计会话列表，中间是该会话对应的工具调用路径。可以看到 Agent 从用户请求开始，依次调用 shell、read_file、process_data，最终试图 external_send 到外部端点。

TraceShield 在 external_send 执行前完成同步审计，并返回 BLOCK。右侧展示了阻断原因、命中策略和工具调用详情。底部 Evidence Path 展示了从用户请求到危险外发的完整证据链。

这说明 TraceShield 不只是记录日志，而是在 Agent 工具调用执行前进行实时审计、风险链路追踪和危险行为阻断。
```
