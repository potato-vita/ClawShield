# 策略与风控

## 双层判定模型

ClawShield 并不是只依赖 Guardrails 单点判断，而是双层判定：

1. 语义层（Guardrails）
   - 判定任务上下文下的动作语义是否可接受
2. 策略层（PolicyEngine）
   - 根据 task/tool/resource 三元关系执行可配置规则

最终决策由 Gateway 汇总为：`allow` / `warn` / `deny`。

## 规则配置文件

规则目录：`configs/rules/`

- `task_tool_map.yaml`
  - 任务类型可用工具与禁用工具
- `tool_resource_map.yaml`
  - 工具到资源类型/路径的限制
- `sensitive_resources.yaml`
  - 敏感资源模式（如 `*_KEY`）
- `risk_chains.yaml`
  - 风险链配置（窗口期、风险等级、处置）

## 匹配器机制

- Task matcher：按 task_type 与 tool_id 匹配
- Tool matcher：按工具特征匹配
- Resource matcher：按资源类型、标识、敏感模式匹配

匹配结果会生成 explain 文本，直接服务报告展示。

## 三个标准风险链

## 1) `chain_workspace_escape`

- 前提：`task_type=analysis`
- 行为：文件访问路径越界（绝对路径或 `..`）
- 结论：高风险，通常 `deny`

## 2) `chain_env_then_http`

- 行为：读取敏感环境变量后，在窗口期内发起 HTTP 外联
- 结论：高风险，通常 `deny`

## 3) `chain_analysis_high_risk_tool`

- 前提：分析任务
- 行为：调用高危工具（如 `danger_exec_plugin`）
- 结论：中高风险，`warn` 或 `deny`

## 扩展建议

新增风险链时建议遵循：

1. 明确链前提（task_type / actor / stage）
2. 明确事件窗口和资源约束
3. 输出可解释结论（给评审可读，而不是仅代码可读）
4. 补单元测试和集成测试
