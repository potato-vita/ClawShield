# TraceShield Core 端到端演示

## 一键运行

```bash
cd core
source .venv/bin/activate
bash scripts/e2e_demo.sh
```

脚本会重置开发数据库并临时启动 `127.0.0.1:8000`，依次验证：

1. README 读取返回 `ALLOW`。
2. `.env` 读取返回 `BLOCK`。
3. `external-upload.com` 返回 `ASK`。
4. before/after 工具事件批量入库。
5. 仪表盘读取真实统计。
6. 查询最新高危事件详情。
7. 创建分析会话并通过 SSE 聊天。
8. 生成并下载 HTML 报告。

脚本结束时会停止临时 Core。日志位于 `/tmp/traceshield-core-e2e.log`。

## 真实 OpenClaw 插件联调

Core 使用 8000 端口，插件需要配置：

```text
core_base_url = http://127.0.0.1:8000
```

然后启动 Core：

```bash
cd core
bash scripts/dev_run.sh
```

插件侧运行：

```bash
cd openclaw-plugin
TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8000 npm run demo:openclaw
```

插件当前 demo 会真实调用配置的 Core，并验证 ALLOW/BLOCK/ASK 与 fallback。
