# Round 04：异步事件入库

## 修改文件

新增 `api/events.py`、`services/event_ingest.py`、`event_projector.py`。

## 新增测试

`tests/test_event_ingest.py` 覆盖单事件、重复事件、before/after 工具投影、agent_end 和坏事件隔离。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_event_ingest.py
bash scripts/smoke_plugin_core.sh
```

通过。E2E 批次 accepted=2、duplicated=0、failed=0。

## 失败与修复

初版 smoke shell JSON 多转义导致 422，且命令替换掩盖 curl 错误；已改为正确 JSON并显式保存命令结果。

## 下一轮风险

仪表盘必须处理空库和时间过滤，不能用固定演示数据。
