# 第 6 轮开发记录

## 时间

2026-06-17

## 本轮目标

实现异步事件队列和失败补传，避免消息、工具结果和任务结束事件丢失。

## 已完成

1. 新增 `src/client/eventClient.ts`，支持批量上报 `/v1/events/batch`。
2. 新增 `src/queue/diskQueue.ts`，按 `event_id` 落盘保存事件。
3. 新增 `src/worker/flushWorker.ts`，支持定时批量 flush。
4. Core 不可用时，将内存事件持久化到磁盘队列。
5. Core 恢复后从磁盘队列读取并补传。

## 说明

异步事件 flush 不阻塞 OpenClaw 工具执行链路。
