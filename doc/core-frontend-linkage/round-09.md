# Round 09：风险证据与链路

## 修改文件

新增 `risk_evidence`、`risk_graph_edges` 模型；审计 API 写入证据和四节点最小风险链，详情 API 返回 JSON。

## 新增测试

审计与详情测试验证 `.env` 至少生成 1 条 evidence 和 3 条 edge。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_audit_api.py tests/test_event_detail_api.py
```

通过。E2E 详情显示 `user_goal → param → tool → sink`。

## 失败与修复

无失败；证据原值仅保存受限 preview 和 sha256。

## 下一轮风险

动态策略优先级和 disabled 状态必须在真实审计路径中生效。
