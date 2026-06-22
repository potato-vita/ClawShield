# Round 08：报告导出

## 修改文件

新增 `services/report_service.py`、`api/reports.py`、reports Schema 和 `reports` 表。

## 新增测试

`tests/test_reports_api.py` 覆盖记录、HTML 文件、下载，以及聊天“生成报告”返回链接。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_reports_api.py
```

通过。报告内容来自 dashboard 数据，下载文件名经过 `Path.name` 限制。

## 失败与修复

无失败。

## 下一轮风险

风险证据值必须脱敏并保存 hash，风险图需要稳定关联 tool_call/run。
