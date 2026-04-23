# 11 测试与质量保障

## 11.1 测试结构

- `tests/unit`: 单元测试（配置、策略、风险链基础能力）。
- `tests/integration`: 集成测试（按 round 演进验证主流程）。

## 11.2 关键测试覆盖

### Unit 覆盖

- 配置加载与 SQLite URL 归一化。
- run 创建与默认状态。
- guardrails 语义判定（含 mock 后端）。
- policy engine 判定（含 false positive 回归）。
- 风险链基本行为。

### Integration 覆盖

- round2: system/task/runs/events 基础链路。
- round3: 语义守卫事件落库。
- round4: gateway 多 action 类型链路。
- round5: 规则阻断与匹配事件。
- round6: timeline 与 run 状态推进。
- round7: graph 与三类风险链。
- round8: report 结构完整性。
- round9: 错误协议稳定性。
- round10: dashboard 场景一键运行。
- roundz11: callback 接线与 session 自动解析。

## 11.3 推荐执行命令

```bash
pytest -q
```

仅执行 callback 相关：

```bash
pytest -q tests/integration/test_roundz11_opencaw_callback.py
```

仅执行策略相关：

```bash
pytest -q tests/unit/test_policy_engine.py tests/integration/test_round5_policy.py
```

## 11.4 回归验证建议（变更后）

如果你改了以下模块，建议至少执行对应集：

- API 层改动：`round9 + round10 + roundz11`
- policy/gateway 改动：`unit policy + round4 + round5 + round7`
- analyzer/report 改动：`round6 + round7 + round8`
- callback 改动：`roundz11`

## 11.5 已知测试注意事项

`tests/integration/test_round2_flow.py` 在 `setUpClass` 中会删除 SQLite 文件重建数据库。

因此建议：

- 不要在运行中的 `dev_start.py` 旁路并发执行全量 pytest。
- 先停止开发服务，再执行全量测试，避免连接到旧文件句柄。

## 11.6 质量门禁建议

- 不允许未覆盖核心路径的规则改动直接合并。
- 新增风险链必须补最少 1 个正例 + 1 个反例测试。
- 新增 API 必须满足统一错误协议。

