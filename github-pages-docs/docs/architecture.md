# 架构设计

## 分层概览

ClawShield 采用清晰分层，避免策略逻辑、执行逻辑和接口层相互耦合。

1. API 层（`app/api`）
   - 请求解析、响应包装、错误传递
2. 服务层（`app/services`）
   - 业务编排（task ingest、tool pipeline、report）
3. 策略层（`app/policy`）
   - 规则加载、匹配、决策解释
4. 网关层（`app/gateway`）
   - 统一动作拦截、执行、审计事件沉淀
5. 分析层（`app/analyzer`）
   - 时间线、证据图、风险链结论
6. 持久化层（`app/models` + `app/repositories`）
   - ORM 模型与查询封装

## 核心模块职责

## GuardrailsService

- 加载 `guardrails/config.yml`
- 推断 task_type（analysis/general）
- 产出语义决策：allow/warn/deny

## GatewayManager

- 基于 action_type 调用 interceptor + executor
- 汇总 PolicyEngine 结果
- 计算最终决策与处置

## RiskAnalyzer

- 基于 run 级事件序列识别行为组合
- 产出风险链命中和最终风险结论

## ReportService

- 聚合 timeline、graph、risk_hits、tool_calls、resources
- 输出页面可直接消费的 report view model

## 数据模型（核心）

- `runs`: 运行主实体，持有最终风险与处置结果
- `tasks`: 原始输入与元数据
- `audit_events`: 标准化审计事件流
- `risk_hits`: 规则命中记录（含风险链）
- `evidence_edges`: 证据边（图关系）
- `audit_reports`: 报告快照（如需持久化扩展）

## 设计原则

- 配置优先：规则从 `configs/rules/*` 读取
- 单一入口：所有动作经 Gateway
- 可追踪性：run_id 贯穿事件、图、报告
- 可演示性：标准案例具备稳定复现路径
