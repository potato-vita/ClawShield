# GitHub Pages 文档站

本目录是 ClawShield 的可发布文档站点源文件。

## 目录结构

- `mkdocs.yml`: 站点配置
- `docs/`: 文档页面
- `requirements.txt`: 站点构建依赖

## 本地启动

```bash
pip install -r github-pages-docs/requirements.txt
mkdocs serve -f github-pages-docs/mkdocs.yml
```

## 发布

手动发布：

```bash
mkdocs gh-deploy -f github-pages-docs/mkdocs.yml --force
```

自动发布：

- 使用 `.github/workflows/deploy-docs.yml`
- 推送 `main` 分支时自动触发
