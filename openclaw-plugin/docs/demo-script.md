# TraceShield OpenClaw 插件演示脚本

## 准备

1. 在 `mock-core` 目录执行 `npm install`。
2. 启动 Mock Core：`npm run dev`。
3. 在 `openclaw-plugin` 目录执行 `npm install && npm run build`。
4. 将 `openclaw.plugin.json` 指向构建后的 `dist/index.js`。

## 本地可见插件展示

如果当前环境还没有真实 OpenClaw 插件 UI，可以先运行本地展示脚本：

```bash
cd mock-core
npm run dev
```

另开一个终端：

```bash
cd openclaw-plugin
npm run demo:openclaw
```

你会看到一个终端版 “OpenClaw 插件展示面板”，包括插件 ID、版本、已注册 Hook、消息采集队列长度，以及工具调用的 `ALLOW`、`BLOCK`、`ASK` 结果。

## 场景 1：正常读取 README

工具调用参数：

```json
{ "tool_name": "file_read", "tool_kind": "file_read", "params": { "path": "README.md" } }
```

预期结果：Mock Core 返回 `ALLOW`，插件放行。

## 场景 2：读取 .env

工具调用参数：

```json
{ "tool_name": "file_read", "tool_kind": "file_read", "params": { "path": ".env" } }
```

预期结果：Mock Core 返回 `BLOCK`，插件阻断。

## 场景 3：读取 SSH 私钥

工具调用参数：

```json
{ "tool_name": "file_read", "tool_kind": "file_read", "params": { "path": "~/.ssh/id_rsa" } }
```

预期结果：Mock Core 返回 `BLOCK`，插件阻断。

## 场景 4：执行 rm -rf

工具调用参数：

```json
{ "tool_name": "shell", "tool_kind": "shell_exec", "params": { "cmd": "rm -rf /tmp/demo" } }
```

预期结果：Mock Core 返回 `BLOCK`，插件阻断。

## 场景 5：访问外部 URL

工具调用参数：

```json
{ "tool_name": "http_request", "tool_kind": "network_request", "params": { "url": "https://example.com" } }
```

预期结果：Mock Core 返回 `ASK`，插件触发人工确认。

## 场景 6：Core 关闭后执行高危命令

关闭 Mock Core 后执行：

```json
{ "tool_name": "shell", "tool_kind": "shell_exec", "params": { "cmd": "rm -rf /tmp/demo" } }
```

预期结果：插件进入本地降级策略，返回 `BLOCK`，并生成 `fallback_decision` 事件。

## 场景 7：Core 关闭后普通只读

若本地 allow cache 命中 `file_read:README.md`，则放行；未命中则进入 `ASK`。

## 场景 8：包含 token 的参数

工具调用参数：

```json
{ "tool_name": "http_request", "params": { "url": "https://example.com", "token": "secret-token" } }
```

预期结果：异步事件中的 token 字段只保留 hash，不上传明文。
