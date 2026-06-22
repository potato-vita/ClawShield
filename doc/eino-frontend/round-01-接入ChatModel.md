# Round 01：接入火山云方舟 Ark ChatModel

## 日期

2026-06-22

## 目标与范围

Round 00 的工作流是纯确定性的：从 Core 取 Dashboard / EventDetail，拼成固定字符串返回。本轮接入真实 LLM（火山云方舟 Ark，OpenAI 兼容协议，endpoint 对应 `deepseek-v4-pro`），让 `/api/analysis` 产出**以真实事件数据为依据的中文安全分析**，取代固定字符串。

凭证写入根目录 `api.md`（`ARK_API_KEY` / `ARK_CHAT_MODEL` / `ARK_EMBEDDING_MODEL` / `ARK_BASE_URL`），代码从环境变量读取，源码内不硬编码。

## 关键设计决策

1. **实现一个真正的 Eino `model.BaseChatModel`**（`ark_chatmodel.go`），而非把 HTTP 调用塞进 lambda 闭包。将来换官方 `eino-ext/.../ark` 只需改工厂一处，链结构不变。
2. **零新增依赖、守住 `go 1.18`**：Ark 客户端仅用 `net/http` + `encoding/json` 自实现，不动 `go.mod`，沿用 vendored 自包含约束。
3. **用 `InvokableLambda` 调 `Generate`，不用 `AppendChatModel` 节点**：`AppendChatModel` 要求节点严格 `[]*schema.Message → *schema.Message`，为透传 `EventIDs`/`Mode` 会被迫用 `context.WithValue` 跨节点隐式携带（脆弱）。改由一段 `InvokableLambda` 接收完整 `analysisContext`，EventIDs/Mode 在闭包内自然流转。
4. **统一单链 + 优雅回退**：只编译一条链。`chatModel == nil`（未配置）或 `Generate` 失败时，自动回退到 Round 00 的确定性答案（`Mode = "fallback"`）。现有测试（传 `nil`）行为完全不变。
5. **安全边界**：Ark 请求体不含 `tools` / `tool_choice`；system prompt 明确禁止命令执行；组装回答只取 `schema.Message.Content`，忽略任何 `ToolCalls`。TraceShield 是只读分析产品。

## 实现内容

| 文件 | 动作 | 说明 |
| --- | --- | --- |
| `eino/examples/traceshield/ark_chatmodel.go` | 新增 | `ArkConfig` + `LoadArkConfig(getenv)`；`NewArkChatModel(cfg)` 返回 `model.BaseChatModel`；OpenAI 兼容请求/响应 JSON 类型；`Generate`（非流式）+ 退化 `Stream`（`schema.StreamReaderFromArray` 单块流）。 |
| `eino/examples/traceshield/workflow.go` | 修改 | 抽出 `buildFallbackAnswer`；`NewAnalysisWorkflow` 增加 `chatModel` 参数；第二段 Lambda 改为「先试 LLM，失败/未配置则回退」；新增中文 system prompt、`buildMessages`、`dashboardContextText`、`eventDetailContextText`、`assembleLLMAnswer`（含 event_id 去重兜底）。 |
| `eino/examples/traceshield/server.go` | 修改 | `NewServer` 内 `LoadArkConfig(os.Getenv)`，启用时构造 model 并打日志；`Server` 加 `chatModelEnabled`；`/api/health` 响应加 `"chat_model"` 字段。 |
| `eino/examples/traceshield/workflow_test.go` | 修改 | 现有用例改传 `nil`；新增 LLM 用例、Ark 500 错误用例、Ark 失败回退用例。 |

`main.go` 不变（启动日志由 `NewServer` 打印）。

## Prompt 设计

- **system**：你是 TraceShield 安全分析助手；只能基于「事件数据」真实事实作答、禁止编造；必须原样保留并引用 `event_xxx`；禁止输出工具调用/命令/写操作；≤200 字、先结论后 2-3 条建议；无数据回「未找到相关事件」。
- **user**：`【TraceShield 事件数据】`（Dashboard 或 EventDetail 序列化成**纯文本**，非 JSON dump，避免 event_id 被转义）+ `【用户问题】`。
- `Evidence` / `RiskGraph` 本轮**不喂模型**，避免敏感信息外泄与巨型 payload（后续轮再评估）。

## 验证

```text
go vet ./examples/traceshield: clean
go test ./examples/traceshield -v: 5 passed（含 LLM / 错误 / 回退，全部不触网）
go test ./...: 46 packages passed（无回归）
```

真实 Ark 连通性（`api.md` 中的 curl，`ep-20260602133449-kmp8g`）：

```text
HTTP 200, 3.47s
choices[0].message.content: "在的"
model: deepseek-v4-pro-260425
```

真实 Ark 穿透工作流冒烟（假 Core 返回两条高危事件 + 真实 Ark，临时用例，验证后删除）：

```text
Mode=llm
Answer:
结论：当前存在 1 条 CRITICAL 和 1 条 HIGH 事件，需立即处置。
优先级：event_a1b2（CRITICAL）> event_c3d4（HIGH）。
建议：
1. 立即核查 event_a1b2 中研发账号非工作时间读取 /etc/passwd 的行为……
2. 针对 event_c3d4 异常外发敏感文件至外部对象存储，阻断相关访问并追溯数据外泄范围。
3. 对涉事账号进行临时禁用并开展安全审查……
```

事件 ID `event_a1b2` / `event_c3d4` 被 LLM 原样保留，前端 `eventIDPattern` 可抽取并保持可点击。

## 运行方式

```bash
# Core 先起（Round 14 已验证 Core 端）：
cd core && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# 导入 Ark 凭证（见根目录 api.md），再起 Eino：
cd eino
export ARK_API_KEY=... ARK_CHAT_MODEL=ep-20260602133449-kmp8g ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
go run ./examples/traceshield
# 启动日志：ChatModel: enabled (model=ep-... base=...)

curl -s -X POST http://127.0.0.1:8080/api/analysis \
  -H 'content-type: application/json' \
  -d '{"message":"最近有哪些风险？"}'
# 期望 Mode=llm，Answer 为 Ark 中文分析，EventIDs 保留 event_xxx

# 未配置 ARK_* 时，同一请求自动回退（Mode=dashboard/event_detail/fallback）
```

## 当前边界与下一步

- 已完成：真实 LLM 分析、确定性回退、事件 ID 透传、go 1.18 零依赖、单测全绿、真实 Ark 端到端验证。
- `Stream` 当前是退化单块流（本端点只走 `Invoke→Generate`）。如需浏览器逐 token 流式，可后续实现真正的 SSE 解析并让 `/api/analysis` 改 SSE 输出。
- 仍未接 Core 真实联调（本机 `core/.venv` 未安装、`requirements.txt` 为空）。Core 侧在 Round 14 已端到端验证；本轮用假 Core + 真实 Ark 完成了 Eino 侧验证。
- `Evidence` / `RiskGraph` 暂未喂模型；后续可评估是否给模型更多风险链路上下文。
