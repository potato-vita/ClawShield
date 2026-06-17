# TraceShield 插件测试报告

## 覆盖范围

1. 插件数据契约：`TraceEvent` 和 `AuditRequest` 的 v1 schema。
2. 决策映射：`ALLOW`、`WARN`、`ASK`、`BLOCK` 和 `modified_params`。
3. 脱敏：token、password、private key、大文本 preview。
4. 本地降级：高风险 fail-closed、敏感文件阻断、只读缓存放行、未知工具审批。
5. 配置读取：source/env/default 优先级、非法配置回退、数组配置读取。
6. HTTP 集成：真实本地 HTTP server 与 `AuditClient` 往返。

## 命令

```bash
npm run typecheck
npm run format:check
npm run test
npm run build
npm run demo:openclaw
```

## 当前结果

2026-06-17 执行结果：

1. `npm run format:check` 通过。
2. `npm run typecheck` 通过。
3. `npm run test` 通过，6 个测试文件、30 个用例全部通过。
4. `npm run build` 通过。
5. `npm run demo:openclaw` 通过，5 个演示场景全部通过。
6. `mock-core` 的 `npm run typecheck` 通过。
7. Mock Core `/v1/audit/tool-call` 对 `rm -rf` 返回 `BLOCK`。
8. 真实 OpenClaw Gateway 验证：`traceshield-security-plugin` 为 `loaded`，真实 agent 调用 `exec rm -rf /tmp/traceshield-codex-check` 时被 TraceShield 阻断。

## 本次新增测试文件

1. `src/tests/config.test.ts`

## 真实验证说明

`demo:openclaw` 是本地链路演示，不等于真实 OpenClaw Gateway 加载验证。真实接入步骤与记录表见 `doc/real-openclaw-integration.md`。
