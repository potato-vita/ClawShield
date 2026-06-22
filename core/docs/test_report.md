# TraceShield Core 验收测试报告

## 环境

- 日期：2026-06-22
- Python：3.12.3
- 数据库：SQLite
- OpenClaw 插件：`@traceshield/openclaw-plugin` 0.1.0

## 自动化测试

```bash
cd core
.venv/bin/pytest -q
```

覆盖数据库、插件协议、审计、事件入库、仪表盘、事件详情、会话 SSE、报告、策略、审批、上传和前端静态页面。

最终结果：`36 passed, 1 warning`。

插件回归：`6 files / 30 tests passed`，format check、typecheck 和 build 均通过。

## 验收场景

| 场景 | 预期 | 验证方式 |
| --- | --- | --- |
| 读取 README.md | ALLOW，保存 tool_call | audit API + DB 测试 |
| 读取 .env | BLOCK，生成 critical security_event | audit API + E2E |
| rm -rf | BLOCK，风险解释为危险命令 | audit API 测试 |
| external-upload.com | ASK，approval pending | audit/approval 测试 |
| after_tool_call | trace_events 和 tool_results 有记录 | event ingest 测试 |
| 查询最近 7 天高危事件 | SSE 回答引用真实事件 ID | sessions API 测试 |
| 导出报告 | HTML 文件可下载 | reports API + E2E |

## 安全约束

- 数据库参数和事件 payload 经过递归脱敏。
- 工具结果只保存 preview/hash/size。
- 上传文档仅保存最多 1000 字符脱敏 preview。
- 默认上传限制 10 MB。
- 文件名经过安全处理。

## 已知提示

当前 FastAPI/Starlette TestClient 会输出一条未来迁移 `httpx2` 的弃用警告，不影响测试与运行结果。
