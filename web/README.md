# TraceShield Web

Vue 3 + Vite + TypeScript 实现的 TraceShield 实时审计工作台。默认入口是 `/runtime`，内置可独立演示的 `payroll-leak-demo`。

## 启动

```bash
cd web
npm install
cp .env.example .env
npm run dev
```

打开 `http://127.0.0.1:5173/runtime`。

## 数据模式

`.env` 默认使用 mock：

```env
VITE_TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787
VITE_USE_MOCK_DATA=true
```

- `true`：完全使用前端 mock，无需 Core/PostgreSQL，适合答辩演示。
- `false`：请求 Core。请求失败时页面保留 mock 数据并显示 fallback 错误，不会白屏。

更改 `.env` 后需重启 Vite。

## Core 接入

当 Core 运行在 `127.0.0.1:8787` 时，将 `VITE_USE_MOCK_DATA` 设为 `false`。前端使用 dashboard、health、audit events、risk graph、evidence path 和 SSE 接口。会话与 run 列表由 audit events 派生，以兼容当前 Core 接口集。

Core 未实现 policies REST 时，Policy Center 会保留布局并显示明确操作提示。

## 验证

```bash
npm run typecheck
npm run build
npm run dev
# 在另一个终端
npm run smoke
```

Smoke check 验证生产构建、核心源文件、演示攻击链标记及四个主要路由。

## 演示路径

1. 进入 Runtime，选择 `Payroll exfiltration`。
2. 点击 `read_file` 查看敏感对象证据。
3. 点击 `external_send` 或 `BLOCKED` 查看阻断决策与证据链高亮。
4. 切换 Assistant 查看风险解释。
5. 打开 Tool Calls、Policies，再点击顶部状态查看 Core 弹层。

`/sessions` 是独立的会话档案页；`/runtime` 专注当前实时审计路径，其内的 Recent Sessions 仅用于切换运行上下文。
