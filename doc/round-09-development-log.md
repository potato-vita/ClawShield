# 第 9 轮开发记录

## 时间

2026-06-17

## 本轮目标

补充测试和演示脚本，让插件部分可以稳定演示。

## 已完成

1. 新增 `src/tests/plugin-contract.test.ts`。
2. 新增 `src/tests/decision-mapping.test.ts`。
3. 新增 `src/tests/sanitizer.test.ts`。
4. 新增 `src/tests/fallback-policy.test.ts`。
5. 新增 `docs/demo-script.md`。
6. 新增 `docs/plugin-test-report.md`。

## 验证

在 `openclaw-plugin` 目录执行：

```bash
npm run typecheck
npm run test
npm run build
```

结果：

1. 类型检查通过。
2. 4 个测试文件、15 个用例全部通过。
3. 构建通过。

在 `mock-core` 目录执行：

```bash
npm run typecheck
```

结果：类型检查通过。

Mock Core 实际接口验证：

```bash
curl -s -X POST http://127.0.0.1:8787/v1/audit/tool-call \
  -H 'content-type: application/json' \
  -d '{"tool_kind":"shell_exec","raw_params":{"cmd":"rm -rf /tmp/demo"},"risk_hint":"shell_exec"}'
```

结果：返回 `BLOCK`。

## 剩余风险

OpenClaw 真实 Hook API 未包含在当前仓库中，因此当前实现使用窄接口 `hooks.on(eventName, handler)` 做宿主适配。接入真实 OpenClaw SDK 时，需要按其官方 API 调整注册入口，但内部事件、审计、队列、脱敏和策略模块可以复用。
