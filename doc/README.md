# TraceShield 文档索引

## 当前入口

- [项目介绍](../PROJECT_OVERVIEW.md)：架构、模块边界、数据流、策略、隐私和部署边界。
- [完整启动手册](../RUNBOOK.md)：人和 Agent 可直接执行的完整启动、验证、主机访问与故障定位流程。

## 正式技术文档

| 范围 | 文档 |
| --- | --- |
| Core HTTP、SSE、审计与方法接口 | [Core API](../core/docs/api.md) |
| CloudWeGo Eino + DeepSeek 对话服务 | [Assistant README](../assistant-eino/README.md) |
| Web `/assistant` 的 Core 代理接口 | [Core API - Security Assistant](../core/docs/api.md#security-assistant) |
| 方法引擎运行模式与验证 | [Method Engine](../core/method-engine/README.md) |
| 方法来源与基线 | [SOURCE](../core/method-engine/SOURCE.md)、[PHASE0_BASELINE](../core/method-engine/PHASE0_BASELINE.md) |
| OpenClaw 插件职责与配置 | [插件契约](../openclaw-plugin/docs/plugin-contract.md) |
| 插件事件格式 | [事件 Schema](../openclaw-plugin/docs/event-schema.md) |
| 插件决策格式 | [决策 Schema](../openclaw-plugin/docs/decision-schema.md) |
| 插件演示流程 | [演示脚本](../openclaw-plugin/docs/demo-script.md) |
| Web 模块说明 | [Web README](../web/README.md) |

## 补充设计与验证资料

以下文件不是日常启动或开发的前置阅读，但保留其技术参考价值：

- `core-postgresql-codex/`：Core 数据库设计和 API 使用说明。
- `core-v2-runtime-method/`：方法引擎验证产物与运行时报告。
- `frontend-codex/`：前端 API 映射和界面设计资料。

过程性的轮次记录、执行计划、进度日志和旧测试记录已从正式文档集合移除。实验论文包、`tex/`、`pic/` 与 `TraceShield_Experiment-main/` 是独立研究资产，不属于运行时产品文档入口。
