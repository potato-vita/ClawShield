# 01 项目总览与术语

## 1.1 项目定位

ClawShield 是一个面向 AI 工具调用场景的“运行时安全审计与治理层”。

系统目标不是替代模型推理，而是把以下能力显式化：

- 工具调用前：做语义与策略判定。
- 工具调用中：统一经过网关执行或阻断。
- 工具调用后：沉淀事件、构建时间线、图谱、风险链。
- 输出层：形成可解释的审计报告与最终处置结论。

## 1.2 适用边界

适用场景：

- OpenClaw 类工具调用代理（tool-calling agent）。
- 需要向评审、审计、竞赛答辩展示“可解释风控链路”的场景。
- 本地可复现演示（默认 SQLite + mock executor）。

不适用场景（当前版本）：

- 大规模高并发生产流量。
- 真实高风险副作用执行（当前执行器为 mock 语义）。
- 完整聊天文本级别审计（当前主链路以 tool-call/result 为核心事件）。

## 1.3 当前实现状态

截至当前代码，系统已具备：

- 任务 ingest -> 守卫判定 -> 策略网关 -> 审计事件 -> 报告生成的完整闭环。
- 风险链识别（3 条标准链）。
- Dashboard、Run Detail、Report 页面。
- OpenClaw callback 回调接入（支持 session 维度自动建 run）。

## 1.4 核心术语

- `run`: 一次任务处理的主上下文单元，对应唯一 `run_id`。
- `task`: 用户输入任务内容，归属到某个 run。
- `audit event`: 规范化事件流，是报告与图谱的事实来源。
- `semantic decision`: 语义守卫给出的 allow/warn/deny 倾向。
- `policy decision`: 策略引擎根据规则得出的 allow/warn/deny 结论。
- `disposition`: 最终处置动作语义（allow/warn/deny/block）。
- `risk finding`: 风险链命中结果（如 `chain_env_then_http`）。
- `report`: run 级聚合结果，面向展示与审计。

## 1.5 关键设计原则（当前版本）

- 单一事实源：事件与结论以持久化数据为准，不依赖跨请求可变缓存。
- 分层清晰：API 层不写业务决策，业务逻辑由 service/policy/analyzer 完成。
- 可解释优先：每次关键判定都要有事件与理由可追踪。
- 演示可复现：默认使用可控 executor 输出，避免外部不确定副作用。

## 1.6 代码目录总览

- `app/api`: HTTP 路由与错误处理。
- `app/services`: 业务编排服务。
- `app/gateway`: 拦截器 + 执行器 + 网关调度。
- `app/policy`: 规则加载、匹配、解释。
- `app/analyzer`: 时间线、证据图、风险链分析。
- `app/repositories`: 持久化读写边界。
- `app/models`: SQLAlchemy 实体。
- `configs`: 应用、桥接、规则配置。
- `scripts`: 初始化、启动、演示数据脚本。
- `tests`: 单元与集成测试。

