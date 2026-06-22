# Round 00：Core FastAPI 基线

## 执行时间

2026-06-22

## 本轮目标

按照任务书第 0 轮，仅建立 TraceShield Core 的最小 FastAPI 服务：

- 创建 `core/` 基础目录。
- 提供 `/api/module4/health`。
- 创建 Python 虚拟环境和依赖说明。
- 建立 pytest 测试框架。
- 回归验证现有 OpenClaw 插件。

本轮没有连接数据库，也没有实现 `/v1/audit/tool-call` 或 `/v1/events/batch`。

## 修改文件

| 文件 | 说明 |
| --- | --- |
| `.gitignore` | 忽略 Python 虚拟环境、缓存和覆盖率产物 |
| `core/.env.example` | Core host/port 环境变量示例 |
| `core/requirements.txt` | FastAPI、Uvicorn、SQLAlchemy、pytest、httpx 等依赖 |
| `core/README.md` | 虚拟环境、测试、启动和 curl 使用说明 |
| `core/app/__init__.py` | Python application package |
| `core/app/config.py` | 最小 Pydantic Settings 配置 |
| `core/app/main.py` | FastAPI 应用入口 |
| `core/app/api/__init__.py` | API package |
| `core/app/api/health.py` | Module 4 health endpoint |
| `core/tests/__init__.py` | tests package |
| `core/tests/conftest.py` | FastAPI TestClient fixture |
| `core/tests/test_health.py` | health API 自动化测试 |

## 新增测试

`core/tests/test_health.py` 验证：

1. `GET /api/module4/health` 返回 HTTP 200。
2. `success` 为 `true`。
3. Round 0 的数据库状态为 `not_initialized`。
4. 服务名为 `traceshield-core`。
5. 版本为 `0.1.0`。

## 环境

```text
Python 3.12.3
Core virtualenv: core/.venv
```

## 执行命令与结果

### 安装依赖

```bash
cd core
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

结果：通过。

### Core pytest

```bash
cd core
.venv/bin/pytest -q
```

结果：

```text
1 passed, 1 warning
```

### Uvicorn 与 curl

```bash
cd core
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -i http://127.0.0.1:8000/api/module4/health
```

结果：HTTP 200。

```json
{
  "success": true,
  "database": "not_initialized",
  "service": "traceshield-core",
  "version": "0.1.0"
}
```

验证后已正常停止临时 Uvicorn 进程。

### OpenClaw 插件回归

```bash
cd openclaw-plugin
npm run typecheck
npm run test
npm run build
```

结果：

```text
typecheck: 通过
test: 6 files / 30 tests 通过
build: 通过
```

## 失败项与警告

没有失败项。

Core pytest 有一条来自当前 FastAPI/Starlette 依赖栈的弃用警告：`starlette.testclient` 提示未来改用 `httpx2`。该警告不影响本轮测试与运行，后续升级依赖时需要重新评估。

虚拟机在首次验证过程中发生重启；重启后重新执行了 Core pytest、插件 typecheck/test/build 和真实 curl，结果均通过。

## 验收结论

- [x] `core/` 可以启动。
- [x] `/api/module4/health` 返回 200。
- [x] pytest 至少 1 个测试通过。
- [x] 插件原有测试继续通过。
- [x] 未修改插件协议。
- [x] 本轮未提前实现数据库或审计业务。

## 下一轮风险点

Round 1 将引入 SQLite 和 SQLAlchemy 8 张核心表，需要重点控制：

1. 测试数据库与开发数据库隔离，避免 pytest 污染 `app/data/traceshield.db`。
2. SQLite 外键应显式开启。
3. ORM 字段必须覆盖任务书 DDL，特别是 JSON 文本、时间字段和外键。
4. health 从 `not_initialized` 切换为真实数据库探测后，异常路径也必须测试。
