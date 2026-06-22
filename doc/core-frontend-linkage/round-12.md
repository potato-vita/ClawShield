# Round 12：会话文档上传

## 修改文件

新增 `uploaded_documents` 表和 `POST /sessions/{id}/docs`，文件保存到 `app/data/uploads/{session_id}`。

## 新增测试

`tests/test_upload_docs_api.py` 覆盖 txt 上传、文件/记录/hash、敏感 preview 脱敏、10MB 限制和非法 session。

## 命令与结果

```bash
.venv/bin/pytest -q tests/test_upload_docs_api.py
```

通过。

## 失败与修复

测试初次把相对 `app/` 的 stored_path 又拼了一次 data；修正测试后通过，生产路径符合任务书。

## 下一轮风险

仓库不存在任务书提到的实验源码，Round 13 不能虚构“已搬运”，需要实现等价纯逻辑并记录差异。
