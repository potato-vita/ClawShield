# Round 11：审批闭环

## 修改文件

新增 `approvals` 表；ASK 审计创建 pending approval；`POST /sessions/{id}/approve` 支持 approved/rejected 并写聊天消息。

## 新增测试

`tests/test_approvals_api.py` 覆盖 ASK 入库、批准、拒绝和不存在 pending approval。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_approvals_api.py
```

通过。

## 失败与修复

无失败。

## 下一轮风险

上传接口必须限制大小、安全处理文件名、计算 hash，数据库只能存脱敏 preview。
