# 02 快速开始与环境准备

## 2.1 环境要求

建议基础环境：

- Python 3.12+
- Linux/macOS（Windows 也可运行，但本文以 Linux 为主）
- 可用终端与浏览器

## 2.2 安装依赖

在项目根目录执行：

```bash
pip install -e .
```

如果你使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2.3 初始化数据库

```bash
python3 scripts/init_db.py
```

成功标志：终端输出 `Database initialized successfully.`

## 2.4 启动服务

```bash
python3 scripts/dev_start.py
```

默认监听：`http://127.0.0.1:8000`

## 2.5 首次可用性检查

```bash
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v1/system/status | python3 -m json.tool
```

预期重点字段：

- `app_status = ok`
- `db_status = ok`
- `guardrails_status = ready`

## 2.6 UI 入口

- Dashboard: `http://127.0.0.1:8000/api/v1/ui/dashboard`
- Swagger: `http://127.0.0.1:8000/docs`

## 2.7 一键演示场景

方式 A：通过 dashboard 按钮执行。

方式 B：直接 API 执行：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/dashboard/scenarios/env_then_http/run | python3 -m json.tool
```

返回中会包含：

- `run_id`
- `report_url`
- `final_risk_level`
- `final_disposition`

## 2.8 OpenClaw callback 最小联通验证

```bash
BASE=http://127.0.0.1:8000/api/v1/bridge/opencaw
SESSION_ID=oc_session_001

curl -s -X POST $BASE/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"'"$SESSION_ID"'","user_input":"请分析仓库并总结风险"}' | python3 -m json.tool

curl -s -X POST $BASE/callback/tool-call \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"'"$SESSION_ID"'","tool_id":"workspace_reader","tool_call_id":"call_1","arguments":{"file_path":"../secret.txt"}}' | python3 -m json.tool
```

## 2.9 常见启动问题快速判断

- 浏览器访问 `/` 返回 404：正常，项目没有定义站点根路由。
- `readonly database`：通常是数据库文件被替换/权限异常/测试与服务并发写导致。
- OpenClaw 显示 running 但无审计更新：只代表进程管理状态，不代表已接线真实 webhook。

详细排障见：[12 运维与故障排查](./12_operations_and_troubleshooting.md)
