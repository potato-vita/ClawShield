# Round 06：事件详情

## 修改文件

新增 `services/event_detail_service.py`，实现 `GET /api/module4/events/{event_id}`，前端右栏接入详情。

## 新增测试

`tests/test_event_detail_api.py` 覆盖存在/不存在事件、工具决策关联、recommended_actions、evidence、risk_graph 和外部网络分类。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_event_detail_api.py
```

通过。

## 失败与修复

E2E 发现 URL 因包含 `/` 被误标为文件；改为优先识别 `network_request`/HTTP URL，并增加回归测试。

## 下一轮风险

会话聊天必须返回可消费 SSE，并让回答中的真实 event ID 可点击。
