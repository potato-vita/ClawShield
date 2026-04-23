# 09 OpenClaw 接入与 Webhook

## 9.1 当前支持的接入模式

### 模式 A：本地演示模式（默认）

- 由 `opencaw_service` 托管占位进程。
- 用于展示系统状态和流程，不代表真实聊天事件接入。

### 模式 B：真实回调接线模式（推荐）

- OpenClaw 侧将工具调用事件以 HTTP webhook 推送到 ClawShield。
- ClawShield 被动接收并入审计链。

## 9.2 必接回调接口

- `POST /api/v1/bridge/opencaw/session/bootstrap`
- `POST /api/v1/bridge/opencaw/callback/tool-call`
- `POST /api/v1/bridge/opencaw/callback/tool-result`

## 9.3 最小接线流程

1. 先 bootstrap session，建立或解析 run。
2. 每次 tool-call 回调到 `callback/tool-call`。
3. 每次 tool-result 回调到 `callback/tool-result`。
4. 通过 `/events` 和 `/runs/{run_id}/report` 验证链路。

## 9.4 回调字段映射建议

### session bootstrap

- 必填：`session_id`, `user_input`

### callback tool-call

至少包含：

- `session_id`
- `tool_call_id`
- `tool_id`
- `arguments`

支持 OpenAI 风格：

- `message.tool_calls[].id`
- `message.tool_calls[].function.name`
- `message.tool_calls[].function.arguments`

### callback tool-result

至少包含：

- `session_id`
- `tool_result.tool_call_id`
- `tool_result.tool_id`
- `tool_result.execution_status`

建议附带：

- `result_summary`
- `raw_result`

## 9.5 网络与部署注意点

- OpenClaw 与 ClawShield 同机可用 `127.0.0.1`。
- 跨机必须用可达 IP/域名，不能继续用 loopback。
- 建议在反向代理层配置 TLS、鉴权与重试策略。

## 9.6 鉴权建议（当前代码未内建）

建议在网关层增加：

- Bearer token 校验。
- HMAC 签名校验。
- IP allowlist。

## 9.7 验证命令示例

```bash
BASE=http://127.0.0.1:8000/api/v1/bridge/opencaw
SESSION_ID=oc_session_001

curl -s -X POST $BASE/session/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"'"$SESSION_ID"'","user_input":"请分析仓库并总结风险"}' | python3 -m json.tool

curl -s -X POST $BASE/callback/tool-call \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"'"$SESSION_ID"'","tool_id":"workspace_reader","tool_call_id":"call_1","arguments":{"file_path":"../secret.txt"}}' | python3 -m json.tool

curl -s -X POST $BASE/callback/tool-result \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"'"$SESSION_ID"'","tool_result":{"tool_call_id":"call_1","tool_id":"workspace_reader","execution_status":"blocked_by_policy_or_semantic_guard","result_summary":"blocked"}}' | python3 -m json.tool
```

## 9.8 为什么“聊天有回复但 Shield 不更新”

常见原因：

- 只发生普通聊天消息，没有触发工具调用回调。
- OpenClaw 回调地址未配置或不可达。
- 回调 payload 不满足最小字段要求。
- 服务端数据库不可写或连接异常。

