# 12 运维与故障排查

## 12.1 运行状态检查清单

按顺序执行：

```bash
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v1/system/status | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v1/rules/summary | python3 -m json.tool
```

重点关注：

- `db_status`
- `guardrails_status`
- `opencaw_status`
- rule 计数是否为 0（0 可能表示规则文件读取异常）

## 12.2 常见问题与处理

### 问题 A：`readonly database`

典型表现：写接口报 `sqlite3.OperationalError: attempt to write a readonly database`。

处理步骤：

1. 停止所有 uvicorn/dev 进程。
2. 删除旧数据库及 wal/shm/journal 文件。
3. 重新 `python3 scripts/init_db.py`。
4. 重启 `python3 scripts/dev_start.py`。
5. 先用 `/tasks/ingest` 验证可写，再做 callback 验证。

### 问题 B：OpenClaw 在聊天，但 Shield 不更新

原因通常是 callback 未接线，不是 API 故障。

检查：

- 是否调用了 `callback/tool-call` 或 `callback/tool-result`。
- OpenClaw webhook 地址是否正确、可达。
- payload 是否带最小必要字段。

### 问题 C：`/` 返回 404

这是预期行为。项目未定义根路由，请使用 `/api/v1/ui/dashboard` 或 `/docs`。

### 问题 D：`RUN_NOT_FOUND_FOR_SESSION`

说明 tool-result 到达时，系统找不到该 session 对应 run。

处理：

- 先调用 `session/bootstrap`。
- 或保证同一 session 的 tool-call 先到达并成功。

## 12.3 日志查看建议

默认日志格式：

- `time level logger msg`

重点关注 logger：

- `app.api.v1.opencaw_bridge`
- `app.services.bridge_service`
- `app.gateway.gateway_manager`
- `app.services.report_service`

## 12.4 启停建议

启动：

```bash
python3 scripts/dev_start.py
```

停止：

- 前台运行时 `Ctrl + C`
- 如残留进程，手动结束对应 uvicorn 进程

## 12.5 生产化建议（当前版本外）

- SQLite 替换为生产数据库。
- 增加 webhook 鉴权与速率限制。
- 增加跨进程日志聚合与 tracing。
- 对 executor 侧 effect 引入沙箱隔离与审计追踪。

