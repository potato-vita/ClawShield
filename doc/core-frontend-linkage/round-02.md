# Round 02：插件协议 Schema

## 修改文件

新增 `app/schemas/plugin.py` 和 `tests/fixtures/plugin_audit_request.json`。

## 新增测试

`tests/test_plugin_contract.py` 覆盖真实插件 fixture、`params`/`raw_params` 双向兼容、默认 context、`type`/`event_type` 和响应序列化。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_plugin_contract.py
```

通过。Core 可解析当前 TypeScript 插件真实请求和任务书样例。

## 失败与修复

无失败。实际协议与任务书存在字段差异，采用兼容而不是修改插件。

## 下一轮风险

同步审计既要返回插件可识别字段，也必须在一个事务内保存 run、call、decision 和 security event。
