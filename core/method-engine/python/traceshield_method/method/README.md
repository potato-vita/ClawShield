# TraceShield Experiment Core

这个包是“从原项目抽取后的实验版 TraceShield 方法核心”。

当前实现来自原项目 `semantic_consistency_experiment/sc_guard/`，不是临时规则器。它保留以下主链路：

- `ToolEvent` -> `SemanticEvent` 工具语义映射；
- 能力边界、资源边界、授权边界；
- 步骤转移一致性、注入诱导漂移、敏感读取后外联；
- 增强 prompt injection 检测；
- 风险图语义关联和数据流传播；
- 高影响工具调用的意图-动作语义关系判断；
- NeMo Guardrails execution rail 接入模板；
- 统一 `AuditResult` 输出，并在每条 `Violation` 中标记 `source`，便于看清风险图、边界规则、注入检测各自贡献。

## 快速使用

安装 `core/method-engine`，或把它的 `python/` 目录加入 `PYTHONPATH`：

```python
from traceshield_method.method import TraceShieldEvaluator, IntentFrame, ToolEvent

intent = IntentFrame(
    task_goal="read public file only",
    allowed_actions=["read_file", "final_answer"],
    allowed_resources=["/tmp/public.txt"],
    forbidden_resources=["/tmp/secret.txt"],
    sensitive_resources=["/tmp/secret.txt"],
)
trace = [
    ToolEvent(step_id=1, tool_name="read_file", args={"path": "/tmp/secret.txt"}),
]
result = TraceShieldEvaluator().evaluate_tool_events("case_001", intent, trace)
```

正式 runner 和 scorer 位于上层实验目录：

- `experiments/traceshield_guardagent_compare/runners/traceshield_runner.py`
- `experiments/traceshield_guardagent_compare/evaluators/validate_dataset.py`
- `experiments/traceshield_guardagent_compare/evaluators/metrics.py`
