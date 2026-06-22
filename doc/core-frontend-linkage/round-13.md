# Round 13：审计引擎增强

## 修改文件

新增 `tool_mapper.py`、`boundary_model.py`、`risk_graph_builder.py`；`AuditEngine` 调用 BoundaryModel，审计 API 调用 RiskGraphBuilder。

## 新增测试

`tests/test_audit_engine.py` 覆盖敏感文件、外部 sink、危险动作和 source-to-sink 节点。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_audit_engine.py tests/test_audit_api.py
```

通过，旧插件协议和旧审计测试未破坏。

## 实际代码差异

仓库搜索不到独立实验代码、runner 或数据集，因此没有可安全抽取的模块。本轮实现任务书描述的纯逻辑边界模型/工具映射/风险图接口，没有虚构实验代码迁移。

## 下一轮风险

最终脚本必须真正失败即退出，避免 curl 错误被 shell 命令替换吞掉。
