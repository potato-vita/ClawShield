# 快速开始

## 环境要求

- Linux / macOS（Windows 建议 WSL）
- Python 3.10+
- 可用网络（如需对接真实 OpenClaw 回调）

## 安装与启动

```bash
cd clawshield
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 scripts/init_db.py
python3 scripts/dev_start.py
```

启动后默认访问：

- Swagger: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/api/v1/health
- Dashboard UI: http://127.0.0.1:8000/api/v1/ui/dashboard

## 首次验证

### 1) 系统状态

```bash
curl -s http://127.0.0.1:8000/api/v1/system/status | jq
```

### 2) 创建任务

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/tasks/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "sess_quickstart",
    "user_input": "请分析项目并总结核心模块",
    "source": "ui"
  }' | jq
```

### 3) 触发工具调用

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/tool-call \
  -H 'Content-Type: application/json' \
  -d '{
    "run_id": "<替换为上一步run_id>",
    "tool_call_id": "tc_quickstart",
    "tool_id": "workspace_reader",
    "arguments": {"file_path": "./workspace/demo.txt"}
  }' | jq
```

### 4) 查看报告

```bash
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/report | jq
```

## 一键演示场景（推荐）

Dashboard 提供标准场景执行接口：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/dashboard/scenarios/workspace_escape/run | jq
curl -s -X POST http://127.0.0.1:8000/api/v1/dashboard/scenarios/env_then_http/run | jq
curl -s -X POST http://127.0.0.1:8000/api/v1/dashboard/scenarios/analysis_high_risk_tool/run | jq
```

每次返回都会附带 `run_id`、`run_detail_url`、`report_url`。
