# ClawShield 开发者指南

> 面向 OpenClaw 工具调用场景的安全治理层，提供语义守卫、策略网关、证据链分析与审计报告。

本指南参考了 NVIDIA NeMo Guardrails 文档的信息组织方式（目录化、模块分层、接口可查、可演示），并结合本项目当前代码状态整理而成。

- 当前文档基线：Round 10 + OpenClaw callback bridge
- 核心能力：
  - 语义守卫：Guardrails 负责候选动作语义判断
  - 策略网关：统一拦截 tool/http/file/env 四类动作
  - 风险链分析：识别三类标准高风险链
  - 报告闭环：时间线 + 证据图 + 最终结论

## 你能在这里找到什么

1. 如何在本地 5 分钟启动系统
2. 每一层架构的职责和边界
3. 从一次 tool call 到最终报告的完整链路
4. 规则文件如何写、风险链如何扩展
5. OpenClaw 实时回调如何接线
6. GitHub Pages 如何部署这套文档站点

## 快速导航

- 如果你是第一次接触项目：先看 [快速开始](quickstart.md)
- 如果你要改规则和风险判断：看 [策略与风控](policy-risk.md)
- 如果你要对接 OpenClaw：看 [OpenClaw 回调接入](opencaw-callback.md)
- 如果你要现场演示：看 [演示与报告](demo-and-report.md)

## 系统全景

```text
OpenClaw / UI
   -> /api/v1/bridge/opencaw/*
      -> GuardrailsService (semantic)
      -> GatewayManager (policy + execution)
      -> AuditService/Telemetry (event stream)
      -> Analyzer (timeline + evidence + risk chains)
      -> ReportService (/runs/{run_id}/report)
```

## 三个标准风险案例

1. `chain_workspace_escape`
   - 分析任务尝试访问工作区外文件（例如 `../secret.txt`）
2. `chain_env_then_http`
   - 读取敏感环境变量后发起外联请求
3. `chain_analysis_high_risk_tool`
   - 分析任务触发高危工具调用

## 文档与代码一致性说明

本页内容综合自以下范围：

- `app/api/v1/*`：真实接口定义
- `app/services/*`：业务编排与错误处理
- `app/analyzer/*`：时间线、证据链、风险分析
- `configs/rules/*`：策略与风险链规则
- `docs/manual/*`、`docs/demo/*`：现有中文手册与演示素材

如接口或字段发生变更，建议优先更新 `docs/manual`，再同步本站点内容。
