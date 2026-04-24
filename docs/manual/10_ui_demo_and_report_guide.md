# 10 UI 演示与报告解读

## 10.1 页面入口

- Dashboard: `/api/v1/ui/dashboard`
- Run Detail: `/api/v1/ui/runs/{run_id}`
- Audit Report: `/api/v1/ui/runs/{run_id}/report`

## 10.2 Dashboard 结构

Dashboard 由三部分构成：

1. 顶部状态区
2. 标准场景执行区
3. 最近 runs + 自由输入建议区

### 10.2.1 顶部状态区

展示：

- ClawShield 状态
- OpenClaw 状态
- Guardrails 状态与 detail

数据来源：

- `/api/v1/system/status`

### 10.2.2 KPI 区

展示：

- 最近 runs 数量
- 高风险 run 数量
- 阻断次数

数据来源：

- `/api/v1/dashboard/overview`

### 10.2.3 场景一键执行

每个场景项包含：

- 场景名
- expected_chain
- prompt
- `run scenario` 按钮

点击后请求：

- `POST /api/v1/dashboard/scenarios/{scenario_id}/run`

成功后会自动跳转到 report 页面。

## 10.3 Run Detail 页面解读

主要用于“事件细节追踪”：

- 左上：run 基础信息（task、task_type、created_at）
- 右上：run 状态（status、risk、disposition）
- 下方表格：按时间顺序列出关键事件
- 页面默认定时轮询，适合演示 OpenClaw 回调的实时入流效果

适用场景：

- 排查“某次决策为什么发生”。
- 对照 event_type 观察流程是否完整。
- 观察 `chat_message_received`、`tool_call_requested`、`resource_access_requested` 的实时变化。

## 10.4 Audit Report 页面解读

Report 页面偏“叙事化审计输出”，关注四块：

1. 审计结论总览（task/risk/disposition/findings）
2. 关键工具调用与资源访问
3. 时间线与图谱摘要
4. 风险命中与最终结论

### 10.4.1 关键字段含义

- `semantic_summary`: 语义层统计摘要。
- `tool_calls`: 报告视角的工具调用列表。
- `resources`: 访问资源汇总与最高风险。
- `risk_hits`: 风险链命中结果。
- `graph.highlighted_paths`: 关键风险路径。
- `conclusion`: 结论文本。

## 10.5 推荐演示话术（可直接照读）

1. “先看 Dashboard，系统与守卫状态正常。”
2. “运行一个标准风险场景，系统自动进入 tool 判定与审计流程。”
3. “切到 Report，看最终风险等级、处置动作与证据链路径。”
4. “如果需要核查细节，回到 Run Detail 看完整事件流。”

## 10.6 演示中常见误解

- 误解：Dashboard 的 OpenClaw running 等于已接入真实聊天。
- 事实：它只代表管理进程状态，真实接入要看 callback 事件是否进入 `/events`。

- 误解：Report 没显示全部事件就是丢数据。
- 事实：Report 是摘要视图，完整事件在 Run Detail。
