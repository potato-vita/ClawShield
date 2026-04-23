# 03 系统架构总览

## 3.1 分层架构

ClawShield 采用清晰分层，核心依赖方向如下：

`API -> Services -> (Policy/Gateway/Analyzer/Repositories) -> Models/DB`

其中：

- API 只负责请求解析、响应封装、错误协议。
- Services 负责业务编排与事务边界。
- Policy/Gateway/Analyzer 分别负责判定、执行、聚合分析。
- Repositories 封装 SQL 访问，避免业务逻辑直接写 SQL。

## 3.2 模块职责

### API 层（`app/api`）

- 注册 v1 路由、HTML 页面、统一错误处理。
- 不直接实现复杂业务判断。

### 服务层（`app/services`）

- `task_service`: 创建 run/task 并记录基础事件。
- `bridge_service`: 处理 tool-call / tool-result 的主流程编排。
- `report_service`: 组装报告所需时间线、图谱、风险结论。
- `demo_service`: 一键运行标准演示场景。
- `opencaw_callback_service`: 外部回调 payload 适配层。

### 策略层（`app/policy`）

- 从 `configs/rules` 读取规则。
- 进行 task/tool/resource 三类匹配。
- 输出 decision、risk、disposition、解释文本。

### 网关层（`app/gateway`）

- interceptor 抽取资源身份（file/env/http/tool）。
- executor 执行受控副作用（当前为 mock）。
- manager 统一合并语义判定与策略判定后给出执行结论。

### 分析层（`app/analyzer`）

- 从事件流构建 timeline。
- 构建证据图节点与边。
- 检测风险链并输出 run 级最终结论。

### 持久化层（`app/models` + `app/repositories`）

- ORM 定义与 CRUD 边界。
- 保持 service 不直接耦合 SQL 细节。

## 3.3 事务边界

典型事务策略：

- API handler 中调用 service 后 `commit`。
- 捕获 `AppError` 时 `rollback` 并原样抛出。
- 捕获未知异常时包装为 `RuntimePipelineError`。

注意：`task_service.ingest_task` 内部会自提交，因为它封装了“建 run + 建 task + 建初始事件”的原子事务。

## 3.4 状态来源

- run 状态由 `TelemetryCollector` 依据事件类型推进。
- 风险等级/处置结论由 risk analyzer 计算后写回 run。
- UI 页面状态从 API 返回数据实时渲染，不依赖共享内存状态。

## 3.5 当前架构约束（重要）

- 不跨请求共享可变中间态。
- 不把 IO/副作用写进核心策略匹配逻辑。
- 规则与策略判定可解释，输出需可审计。
- 默认执行器是 mock 语义，真实执行需单独硬化。

