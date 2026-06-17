# 第 3 轮开发记录

## 时间

2026-06-17

## 本轮目标

接入工具调用 Hook，观察 `before_tool_call` 和 `after_tool_call`，生成标准 `TraceEvent`。

## 已完成

1. 新增 `src/hooks/toolHooks.ts`。
2. 新增 `src/events/normalizeToolCall.ts`，提取工具名、工具类别、参数摘要、资源提示和风险提示。
3. 新增 `src/events/normalizeToolResult.ts`，记录工具结果 preview、hash 和摘要。
4. 支持本地推断 `file_read`、`file_write`、`file_delete`、`shell_exec`、`network_request`、`message_send`、`plugin_install`、`state_change`、`unknown`。

## 说明

Hook 适配层使用 `hooks.on(eventName, handler)` 形式，后续接真实 OpenClaw API 时只需要调整适配入口。
