# 第 7 轮开发记录

## 时间

2026-06-17

## 本轮目标

实现脱敏和最小采集，避免插件上传完整敏感内容。

## 已完成

1. 新增 `src/sanitizer/redact.ts`，覆盖 token、api key、password、secret、cookie、private key。
2. 新增 `src/sanitizer/hash.ts`，提供 SHA-256 hash。
3. 新增 `src/sanitizer/preview.ts`，默认长文本只保留 500 字 preview。
4. 消息事件、工具调用摘要和工具结果默认走脱敏、摘要和 hash。
5. `debug_full_payload` 默认关闭。

## 验证

`sanitizer.test.ts` 覆盖 secret assignment、private key、敏感对象字段和长文本截断。
