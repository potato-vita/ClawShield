# 运维与部署

## 运行排障速查

## 1) 健康与状态

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/system/status
```

## 2) 事件回放

```bash
curl -s "http://127.0.0.1:8000/api/v1/events?run_id=<run_id>&order=asc&limit=500"
```

## 3) 报告与图校验

```bash
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/graph
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/report
```

## 已知限制（当前版本）

1. 默认使用 SQLite，本地复现友好但不适合高并发生产。
2. Executor 以受控/mock 风格为主，真实副作用执行需额外加固。
3. 重点覆盖三条标准风险链，长尾链路需继续补规则。
4. `exec` 动作识别是启发式规则，对混淆命令存在漏判可能。

---

## GitHub Pages 部署

本目录已按 MkDocs 结构组织：

- 配置：`github-pages-docs/mkdocs.yml`
- 文档源：`github-pages-docs/docs/`

## 本地预览

```bash
cd clawshield
python3 -m venv .venv
source .venv/bin/activate
pip install -r github-pages-docs/requirements.txt
mkdocs serve -f github-pages-docs/mkdocs.yml
```

预览地址：`http://127.0.0.1:20000/`

说明：

- 文档站默认使用 `20000`，避免与 FastAPI 应用 `8000` 端口冲突。
- 如果你在浏览器保留了旧的业务页面标签页（例如 `/api/v1/ui/runs/...`），切到 MkDocs 服务后可能看到 404 日志，这是旧页面请求打到了文档服务，不影响文档构建。
- Material 主题的 MkDocs 2.0 预警可通过环境变量关闭：

```bash
NO_MKDOCS_2_WARNING=true mkdocs serve -f github-pages-docs/mkdocs.yml
```

## 手动发布到 gh-pages 分支

```bash
cd clawshield
source .venv/bin/activate
pip install -r github-pages-docs/requirements.txt
mkdocs gh-deploy -f github-pages-docs/mkdocs.yml --force
```

## GitHub 仓库设置

1. 打开仓库 Settings -> Pages
2. Source 选择 Deploy from a branch
3. Branch 选择 `gh-pages`，目录选择 `/ (root)`
4. 保存后等待几分钟生效

## 自动化发布（推荐）

已提供 GitHub Actions 工作流：`.github/workflows/deploy-docs.yml`

触发条件：

- 推送到 `main` 且修改了 `github-pages-docs/**`
- 手动触发 workflow_dispatch

发布后访问：

`https://<你的GitHub用户名>.github.io/<你的仓库名>/`
