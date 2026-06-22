# Round 10：动态策略

## 修改文件

新增 `policies` 表和 `api/policies.py`；RuleEngine 在内置规则前读取 enabled policies，按 priority 降序匹配 contains 条件。

## 新增测试

`tests/test_policies_api.py` 覆盖创建、列表、关闭、高优先级先匹配，以及 BLOCK/WARN 动作。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_policies_api.py tests/test_audit_api.py
```

通过。动态禁止 `secret.txt` 会影响真实审计结果。

## 失败与修复

无失败。

## 下一轮风险

ASK 的 approval 必须关联 session/tool/decision，并处理没有 pending 审批的错误。
