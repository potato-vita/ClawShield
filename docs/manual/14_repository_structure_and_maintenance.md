# 14 项目结构与维护规范

本章给维护者一份“如何持续演进本仓库”的落地规范，目标是：

- 目录职责清晰，可快速定位代码。
- 依赖方向稳定，避免循环依赖与隐式耦合。
- 新需求落地时优先复用现有抽象，避免冗余代码。

## 14.1 顶层目录职责

- `app/`: 后端核心实现（API、业务服务、策略、网关、分析、存储访问）。
- `configs/`: YAML 配置（策略规则、应用配置）。
- `docs/manual/`: 面向维护者和评审者的说明书（以“当前代码”为准）。
- `docs/demo/`: 演示步骤、话术与回调接线。
- `scripts/`: 本地开发脚本（初始化、启动、种子数据）。
- `tests/`: `unit + integration + e2e` 测试。
- `data/`: 本地运行数据（默认 SQLite 数据库）。

## 14.2 app 目录分层约定

- `app/api/`: HTTP 协议层。职责仅限参数接收、响应封装、异常映射。
- `app/services/`: 用例编排层。负责跨模块协作，不直接承担底层 IO 细节。
- `app/gateway/`: 工具调用入口（interceptor + policy + executor）。
- `app/policy/`: 规则加载、匹配与解释。
- `app/repositories/`: 数据访问（ORM 查询、写入封装）。
- `app/analyzer/`: 时间线、证据链、风险链分析。
- `app/reports/`: 报告聚合与展示数据组装。
- `app/schemas/`: API 与内部数据结构（Pydantic）。

依赖方向要求：

- `api -> services -> (gateway/policy/analyzer/repositories)`
- `repositories` 不依赖 `services` 或 `api`
- `analyzer/reports` 不依赖 `api`
- 禁止跨层回调导致隐式时序依赖

## 14.3 去冗余与职责边界（当前基线）

### 统一动作识别入口

动作识别已集中到：

- `app/gateway/action_intent.py`

该模块负责：

- 从结构化参数识别 `http / env_read / file_read / tool_call`
- 解析 `exec/command` 文本并补齐规范字段（如 `url`、`env_key`、`file_path`）
- 为下游 interceptor 提供稳定输入，避免各处重复猜测

`bridge_service` 不再维护独立的动作推断逻辑，避免同一规则在多处漂移。

### interceptor 保持最小职责

- `interceptor` 只做“将规范参数映射到 resource_type/resource_id”。
- 不在 interceptor 中重复做复杂语义解析。
- 不引入中间缓存状态。

## 14.4 代码变更准入清单

提交前至少满足：

1. 无未使用变量、函数、导入。
2. 新逻辑有对应测试（至少 unit 或 integration）。
3. API/规则/行为变更已同步更新 `docs/manual`。
4. 不新增“同一事实多处维护”的状态。
5. 异常不吞掉；统一返回标准错误协议。

## 14.5 测试分层建议

- `unit`: 纯函数和规则匹配（快速、确定性）。
- `integration`: API 到数据库的真实链路（重点覆盖回调与报告）。
- `e2e`: 面向真实部署路径的 smoke 测试（可选）。

新增功能优先补以下两类断言：

- 行为断言：接口返回与状态变更正确。
- 证据断言：`events/timeline/report` 能观察到完整审计链。

## 14.6 Git 与构建产物规范

- 构建产物（如 `*.egg-info`、`build/`、`dist/`）不入库。
- 本地缓存（如 `.pytest_cache/`、`__pycache__/`）不入库。
- 数据文件（`*.db`）不入库，按脚本可重建。
- 每次发版前执行一次全量关键回归测试。

## 14.7 文档维护策略

当发生以下变化时，必须同步更新 manual：

- 回调 payload 字段映射策略变化
- 风险链判定条件变化
- API 路径或错误码变化
- 项目目录职责变化

建议在 PR 描述中固定三个小节：

- `Behavior Change`
- `Test Evidence`
- `Docs Updated`
