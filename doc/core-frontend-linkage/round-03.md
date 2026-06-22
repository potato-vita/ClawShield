# Round 03：同步审计 API

## 修改文件

新增 `api/audit.py`、`services/audit_engine.py`、`rule_engine.py`、`sanitizer.py`、`idgen.py` 和时间解析工具。

## 新增测试

`tests/test_audit_api.py` 覆盖 `rm -rf`、`.env`、`id_rsa`、外部上传、README、未知工具及数据库持久化。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_audit_api.py
TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8000 npm run demo:openclaw
```

通过。真实插件 demo 使用 Core 8000 端口，5/5 场景通过。

## 失败与修复

无协议失败。参数写库前统一递归脱敏，不保存 token/password 私密原文。

## 下一轮风险

事件批处理必须单条失败隔离，并用 event_id 幂等，不能让一个坏事件回滚整批。
