# ClawShield Demo

ClawShield 是一个面向工具调用型 Agent 的安全审计 Demo，具备以下核心能力：

- 统一安全接管网关（文件/工具/网络/命令/环境变量）
- 多维边界建模（资源边界、能力边界、可信边界）
- 运行时事件采集与结构化日志
- 调用链追踪（run -> skill -> tool -> resource）
- 风险规则引擎（基础规则 + 关联规则 R7）
- 审计报告生成（数据库 JSON + HTML 导出）
- Web UI 一键演示场景

## 快速开始

1. 创建并激活虚拟环境（可选）

```bash
python -m venv .venv
source .venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 初始化数据库与种子规则

```bash
python scripts/init_db.py
python scripts/seed_demo_data.py
```

4. 启动服务

```bash
python scripts/run_demo.py
```

5. 打开页面

- 首页: http://127.0.0.1:8000/
- 场景页: http://127.0.0.1:8000/demo

## 三个核心演示场景

- `normal`: 正常任务（工作区读写 + 授权工具）
- `workspace_escape`: 越界访问（读取 `/etc/passwd`，应被阻断）
- `sensitive_exfiltration`: 读取 `.env` 后外联（命中关联风险 R7）

附加场景：

- `unauthorized_tool`
- `dangerous_command`
- `advanced_intrusion_kill_chain`（多阶段高危攻击链，命中多条关联规则）

## 项目结构

参考 `app/`, `rules/`, `scripts/`, `tests/` 目录，整体按展示层、服务层、安全核心层、适配层和持久层组织。

## 关键约束

- 危险命令和外联请求均为模拟/受控，不会真实执行破坏性动作。
- 所有关键行为都必须经过 `SecurityGateway`。
