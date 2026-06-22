# Round 00：上游源码部署与前端基线

## 日期

2026-06-22

## 上游源码

- 仓库：https://github.com/cloudwego/eino
- 分支：`main`
- Commit：`e8832e223b93a7f45b1cc3d491239c14f94717c0`
- 本地目录：`eino/`

原 `eino/` 最小 sandbox 已移到 `/tmp/traceshield-eino-sandbox-backup-20260622`，不再作为应用基础。

## 架构

```text
Browser :8080
  -> TraceShield Eino Go Service
     -> Eino compose workflow
     -> Core reverse proxy
        -> FastAPI Core :8000
        -> SQLite
```

TraceShield 自定义代码位于 `eino/examples/traceshield/`，未直接修改 Eino 核心组件。

## 实现内容

1. 完整部署 CloudWeGo Eino 上游源码。
2. 使用 `compose.NewChain` 创建安全分析工作流。
3. 从 Core 查询 dashboard 和 event detail。
4. 通过 `/api/analysis` 返回 Eino 分析结果。
5. 通过 `/core/*` 代理 Core API。
6. 将 Eino 的 user/assistant 消息回写 Core `chat_messages`。
7. 在 Go binary 中 embed 三栏前端。

## 验证

```text
go test ./examples/traceshield: passed
go test ./...: passed
Core sessions pytest: 3 passed
GET :8080/api/health: passed
GET :8080/: passed
POST :8080/api/analysis: passed
Core session render contains Eino messages: passed
```

## 修复记录

上游 `go.mod` 使用 `go 1.18`，初版采用 Go 1.22 的 ServeMux method pattern，运行时按旧语义导致 `/api/health` 404。已改成路径路由加显式 method 校验，并新增回归测试。

## 当前边界

当前 Eino 工作流使用确定性 compose 节点和真实 Core 数据，还没有配置具体 ChatModel。下一步可以按部署环境接入 OpenAI-compatible、Ollama、Ark 等 EinoExt ChatModel，实现模型生成但保留数据库工具和安全边界。
