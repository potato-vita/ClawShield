# Round 05：仪表盘与前端首页

## 修改文件

新增 `services/dashboard_service.py`、`api/module4.py` 和 `app/static/index.html`；首页挂载到 `/`。

## 新增测试

`tests/test_dashboard_api.py` 覆盖空库、统计、趋势、部门、用户、高危列表和时间范围；`test_frontend.py` 验证首页。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_dashboard_api.py tests/test_frontend.py
bash scripts/smoke_frontend_api.sh
```

通过。三栏工作台展示真实数据库统计，响应式布局在窄屏顺序堆叠。

## 失败与修复

无失败。

## 下一轮风险

事件详情必须正确区分 URL 与文件路径，并关联决策、证据和工具调用。
