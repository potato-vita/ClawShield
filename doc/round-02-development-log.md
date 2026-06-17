# 第 2 轮开发记录

## 时间

2026-06-17

## 本轮目标

接入消息类 Hook，将消息、模型输入输出、发送前消息和任务结束事件转换成 `TraceEvent` 并写入内存队列。

## 已完成

1. 新增 `src/hooks/messageHooks.ts`，注册 `message_received`、`llm_input`、`llm_output`、`message_sending`、`agent_end`。
2. 新增 `src/events/normalizeMessage.ts`，统一生成 v1 `TraceEvent`。
3. 新增 `src/queue/memoryQueue.ts`，支持事件入队、批量出队、重入队和幂等去重。
4. 新增上下文规范化工具，为事件补齐 `session_id`、`run_id`、`trace_id`。

## 说明

本轮只采集和入队，不请求 Core，不阻断 OpenClaw 正常回复。
