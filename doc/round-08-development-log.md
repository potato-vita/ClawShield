# 第 8 轮开发记录

## 时间

2026-06-17

## 本轮目标

实现 Core 故障时的本地保守策略。

## 已完成

1. 新增 `src/policy/fallbackPolicy.ts`。
2. 新增 `src/policy/localPolicyCache.ts`。
3. Core 超时或不可用时，高风险工具 fail-closed。
4. 敏感文件读取默认阻断。
5. 低风险只读工具仅在本地 allow cache 命中时放行。
6. 未知工具默认 `ASK`，审批默认超时阻断。
7. 所有 fallback 决策带 `fallback_used: true`，并生成 `fallback_decision` 事件。

## 验证

`fallback-policy.test.ts` 覆盖高危阻断、敏感读取阻断、缓存只读放行和未知工具审批。
