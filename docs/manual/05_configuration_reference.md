# 05 配置说明

## 5.1 配置加载顺序

`app/settings.py` 的加载逻辑是：

1. 从环境变量（前缀 `CLAWSHIELD_`）读取初始值。
2. 读取 `config_path` 指向的 YAML（默认 `configs/app.yaml`）。
3. 合并后再用“显式设置的环境变量”覆盖。
4. 归一化 `database_url`（相对 SQLite 路径转绝对路径）。

## 5.2 `configs/app.yaml`

默认内容：

```yaml
app_name: ClawShield
app_version: 0.1.0
app_env: dev
host: 127.0.0.1
port: 8000
database_url: sqlite:///./data/clawshield.db
log_level: INFO
openclaw_auto_launch: false
```

字段说明：

- `app_name`: FastAPI 服务名。
- `app_version`: 服务版本号。
- `app_env`: 环境标识（dev/demo 等）。
- `host` / `port`: `uvicorn` 监听地址。
- `database_url`: SQLAlchemy 连接串。
- `log_level`: Python logging 等级。
- `openclaw_auto_launch`: 应用启动时是否自动调用 `opencaw_service.start`。

## 5.3 环境变量覆盖

支持通过 `.env` 或系统环境变量覆盖，例如：

```bash
export CLAWSHIELD_HOST=0.0.0.0
export CLAWSHIELD_PORT=8000
export CLAWSHIELD_DATABASE_URL=sqlite:///./data/clawshield.db
```

## 5.4 OpenClaw 桥接配置 `configs/opencaw_bridge.yaml`

默认：

```yaml
enabled: true
mode: placeholder
launch_command: ""
health_check_url: ""
timeout_seconds: 10
```

要点：

- `mode: placeholder` 且 `launch_command` 为空时，会启动占位进程（sleep）。
- 这只表示“进程托管状态”，不代表“真实事件已接线”。
- 若要托管真实进程，需要提供有效 `launch_command`。

## 5.5 Guardrails 配置 `guardrails/config.yml`

当前是 minimal profile，主要用于：

- 注册基础 rail 分段（input/dialog/execution/output）。
- 注册动作模块（task_context/policy/audit）。
- 暴露 `explain` 与 `verbose` 开关。

该配置是语义守卫上下文，不等价于策略规则文件。

## 5.6 策略规则配置 `configs/rules/*`

### 5.6.1 `task_tool_map.yaml`

定义“任务类型可用工具白/黑名单”。

### 5.6.2 `tool_resource_map.yaml`

定义“某工具可访问哪些资源模式”。

### 5.6.3 `sensitive_resources.yaml`

定义“敏感资源模式命中时的敏感等级”。

### 5.6.4 `risk_chains.yaml`

定义风险链模板（当前 analyzer 里主要是代码内置三条 canonical chain，用于展示）。

## 5.7 风险等级映射 `configs/risk_levels.yaml`

定义 low/medium/high/critical 对应的处置语义说明。

## 5.8 配置变更建议

- 规则变更先走测试，再发布。
- 生产环境数据库请替换 SQLite。
- 真实执行器启用前，先完成 side effect 审计与超时策略设计。

