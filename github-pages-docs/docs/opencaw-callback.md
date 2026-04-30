# OpenClaw 回调接入

本章节对应接口：

- `/api/v1/bridge/opencaw/session/bootstrap`
- `/api/v1/bridge/opencaw/callback/tool-call`
- `/api/v1/bridge/opencaw/callback/tool-result`
- `/api/v1/bridge/opencaw/callback/message`

## 设计目标

- 兼容不同 OpenClaw / Agent payload 形状
- 在缺少 `run_id` 时基于 `session_id` 自动关联或创建 run
- 把外部消息与工具行为统一映射到 ClawShield 标准事件

## 1) 会话 bootstrap

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bridge/opencaw/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "sess_callback_001",
    "user_input": "请分析这个仓库"
  }'
```

返回 `run_id` 供后续 callback 使用。

## 2) tool-call 回调（兼容多形状）

支持示例：

### Shape A：单条直传

```json
{
  "session_id": "sess_callback_001",
  "tool_call_id": "tc_001",
  "tool_id": "env_reader",
  "arguments": {"env_key": "OPENAI_API_KEY"}
}
```

### Shape B：列表模式

```json
{
  "session_id": "sess_callback_001",
  "tool_calls": [
    {
      "id": "call_1",
      "function": {
        "name": "http_fetcher",
        "arguments": "{\"url\":\"https://example.com/upload\"}"
      }
    }
  ]
}
```

## 3) tool-result 回调

```json
{
  "session_id": "sess_callback_001",
  "tool_results": [
    {
      "tool_call_id": "tc_001",
      "tool_id": "env_reader",
      "execution_status": "ok",
      "result_summary": "env value retrieved"
    }
  ]
}
```

## 4) message 回调

```json
{
  "session_id": "sess_callback_001",
  "messages": [
    {"role": "user", "content": "请继续分析"},
    {"role": "assistant", "content": "已完成分析"}
  ]
}
```

系统会写入事件 `chat_message_received`，用于 run 级会话轨迹还原。

## 接线建议

1. 让 OpenClaw 在创建会话后先调用 `session/bootstrap`
2. 工具调用统一发到 `callback/tool-call`
3. 工具结果统一发到 `callback/tool-result`
4. 聊天消息（无工具调用）发到 `callback/message`
5. 通过 `GET /api/v1/runs/{run_id}/report` 校验链路是否闭环
