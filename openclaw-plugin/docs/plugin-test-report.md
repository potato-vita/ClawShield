# TraceShield 插件测试报告

## 覆盖范围

1. 插件数据契约：`TraceEvent` 和 `AuditRequest` 的 v1 schema。
2. 决策映射：`ALLOW`、`WARN`、`ASK`、`BLOCK` 和 `modified_params`。
3. 脱敏：token、password、private key、大文本 preview。
4. 本地降级：高风险 fail-closed、敏感文件阻断、只读缓存放行、未知工具审批。

## 命令

```bash
npm run typecheck
npm run test
npm run build
```

## 当前结果

2026-06-17 执行结果：

1. `npm run typecheck` 通过。
2. `npm run test` 通过，4 个测试文件、15 个用例全部通过。
3. `npm run build` 通过。
4. `mock-core` 的 `npm run typecheck` 通过。
5. Mock Core `/v1/audit/tool-call` 对 `rm -rf` 返回 `BLOCK`。
