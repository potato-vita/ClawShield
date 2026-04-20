# ClawShield

> Security auditing for AI agent tool calls.  
> 面向 AI Agent 工具调用场景的安全审计系统。

## Language

- [English](./README.en.md)
- [简体中文](./README.zh-CN.md)

## Quick Intro

ClawShield is a research-oriented security system for OpenClaw-style agent workflows. It focuses on improving the safety, observability, and controllability of tool invocation across the full execution path.

ClawShield 面向 OpenClaw 类 Agent 执行流程，聚焦工具调用链路中的安全问题，致力于提升系统在真实运行过程中的安全性、可观测性与可控性。

## Status

This project is currently under active design and implementation. More architecture details, module documentation, and usage instructions will be added as the project evolves.

项目目前处于持续设计与实现阶段，后续将逐步补充更完整的架构说明、模块文档与使用指南。

## Demo Usage

ClawShield Demo 是一个面向工具调用型 Agent 的安全审计演示系统，具备以下核心能力：

- 统一安全接管网关（文件/工具/网络/命令/环境变量）
- 多维边界建模（资源边界、能力边界、可信边界）
- 运行时事件采集与结构化日志
- 调用链追踪（run -> skill -> tool -> resource）
- 风险规则引擎（基础规则 + 关联规则 R7/R8/R10/R11）
- 审计报告生成（数据库 JSON + HTML 导出）
- Web UI 一键演示场景

### Quick Start

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 初始化数据库与种子规则

```bash
python scripts/init_db.py
python scripts/seed_demo_data.py
```

3. 启动服务

```bash
python scripts/run_demo.py
```

4. 打开页面

- 首页: http://127.0.0.1:8000/
- 场景页: http://127.0.0.1:8000/demo

### Core Demo Scenarios

- `normal`: 正常任务（工作区读写 + 授权工具）
- `workspace_escape`: 越界访问（读取 `/etc/passwd`，应被阻断）
- `sensitive_exfiltration`: 读取 `.env` 后外联（命中关联风险 R7）
- `unauthorized_tool`: 未授权工具调用（应被阻断）
- `dangerous_command`: 高危命令执行（应被阻断）
- `advanced_intrusion_kill_chain`: 多阶段高危攻击链，命中多条关联规则

### Project Structure

参考 `app/`, `rules/`, `scripts/`, `tests/` 目录，整体按展示层、服务层、安全核心层、适配层和持久层组织。

### Security Notes

- 危险命令和外联请求均为模拟/受控，不会真实执行破坏性动作。
- 所有关键行为都必须经过 `SecurityGateway`。
