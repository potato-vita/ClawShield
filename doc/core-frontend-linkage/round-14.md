# Round 14：端到端验收

## 修改文件

新增 `scripts/dev_run.sh`、`smoke_plugin_core.sh`、`smoke_frontend_api.sh`、`e2e_demo.sh`，以及 `core/docs/e2e_demo.md`、`test_report.md`。

## 自动化与联调结果

```text
Core pytest: 36 passed
Plugin format:check: passed
Plugin typecheck: passed
Plugin tests: 6 files / 30 tests passed
Plugin build: passed
Plugin demo against Core :8000: 5/5 passed
smoke_plugin_core.sh: passed
smoke_frontend_api.sh: passed
e2e_demo.sh: 9/9 steps passed
```

## E2E 覆盖

ALLOW、BLOCK、ASK、事件入库、仪表盘、事件详情、SSE 会话、真实 event ID、HTML 报告生成和下载均通过。

## 失败与修复

独立 smoke 初版 JSON 转义错误返回 422，且 `echo "$(command)"` 未可靠传播失败。已改为合法 JSON参数和显式变量赋值，修复后通过。

## 验收结论

任务书 Round 1–14 已完成。Core 可替代 mock-core；数据库、三栏前端和插件协议形成完整闭环。唯一非失败提示是当前 Starlette TestClient 的未来 `httpx2` 弃用警告。
