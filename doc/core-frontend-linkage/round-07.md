# Round 07：会话与 SSE 聊天

## 修改文件

新增 `api/sessions.py`、`services/session_service.py` 和 sessions Schema；前端左栏/中栏接入会话和聊天。

## 新增测试

`tests/test_sessions_api.py` 覆盖创建、列表、软删除、聊天双向消息入库、SSE render、事件 ID 引用和 abort。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_sessions_api.py
bash scripts/smoke_frontend_api.sh
```

通过。回答引用真实 `security_events` ID，前端可点击打开右栏详情。

## 失败与修复

无失败。

## 下一轮风险

报告文件路径必须限制在 exports 目录，下载接口要避免路径穿越。
