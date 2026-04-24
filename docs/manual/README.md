# ClawShield 说明书（Manual）

本目录是 ClawShield 的完整项目说明书，面向以下读者：

- 项目维护者：快速理解系统边界、核心流程、配置与扩展方式。
- 评审与答辩人员：按证据链追踪系统如何给出风险结论。
- 集成方（如 OpenClaw 侧）：按接口和回调规范完成接入。
- 运维人员：按排障手册定位问题并恢复服务。

当前文档基线对应代码状态：Round 10 + OpenClaw callback bridge（截至 2026-04-24）。

## 阅读路径建议

如果你是第一次接触本项目，建议按顺序阅读：

1. [01 项目总览与术语](./01_overview_and_glossary.md)
2. [02 快速开始与环境准备](./02_quick_start_and_setup.md)
3. [03 系统架构总览](./03_architecture_overview.md)
4. [04 核心流程与时序](./04_core_flows_and_sequences.md)
5. [05 配置说明](./05_configuration_reference.md)
6. [06 数据库与数据模型](./06_data_model_and_storage.md)
7. [07 API 接口说明](./07_api_reference.md)
8. [08 策略与风控说明](./08_policy_and_risk_engine.md)
9. [09 OpenClaw 接入与 Webhook](./09_opencaw_integration_and_webhook.md)
10. [10 UI 演示与报告解读](./10_ui_demo_and_report_guide.md)
11. [11 测试与质量保障](./11_testing_and_quality.md)
12. [12 运维与故障排查](./12_operations_and_troubleshooting.md)
13. [13 开发约束与扩展指南](./13_development_constraints_and_extension.md)
14. [14 项目结构与维护规范](./14_repository_structure_and_maintenance.md)

## 与现有 docs 的关系

`docs/manual/` 是“说明书视角”的整合文档。
已有目录仍保留并继续有效：

- `docs/architecture/`: 模块责任、时序、数据模型草图。
- `docs/demo/`: 演示话术、场景、回调接线说明。
- `docs/spec/`: 早期阶段草案和范围边界。

推荐做法是：

- 日常开发优先看 `docs/manual/`。
- 需要展示流程图和历史决策时，补充查阅 `docs/architecture/` 与 `docs/spec/`。

## 版本维护约定

每次涉及下面任一变化，应同步更新 manual：

- API 路径、请求字段、错误码语义变更。
- 规则配置文件结构变更。
- 风险链判定逻辑变更。
- 数据库表结构变更。
- 演示流程或 UI 关键行为变更。

建议在 PR 中把文档更新作为显式检查项，避免“代码已变、说明书未更新”。
