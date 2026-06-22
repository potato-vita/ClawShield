# Round 01：SQLite 与核心表

## 修改文件

新增 `app/db/base.py`、`session.py`、`models.py`、`init_db.py`、`repositories.py`、`seed.py`，以及 `scripts/reset_db.sh`；更新 config、health 和应用 lifespan。

## 新增测试

`tests/test_db_models.py`：验证 8 张核心表及 session/tool_call/audit_decision/security_event 插入查询。health 测试更新为 `database=ok`。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_db_models.py tests/test_health.py
bash scripts/reset_db.sh
```

通过。最终数据库包含任务书 8 张核心表，并包含后续轮次 6 张扩展表。

## 失败与修复

测试初次发现 `init_db` 捕获旧 engine，测试数据库未建表。改为运行时读取当前 engine，确保开发库和 pytest 临时库隔离。

## 下一轮风险

真实插件使用 `raw_params` 和 Unix 毫秒时间戳，Schema 必须兼容任务书的 `params`/ISO 时间写法。
