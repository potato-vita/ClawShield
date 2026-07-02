# TraceShield 启动指南

本文件汇总在**本机**把 TraceShield 全套跑起来所需的全部命令，包括 PostgreSQL、持久化 Core、实时 Web 控制台、插件构建，以及 OpenClaw Gateway / Chat（直接登录，免交互）。

> 阅读前提：所有 `cd` 路径都以仓库根目录 `traceshield/` 为基准。

> **当前运行状态（2026-07-01 已验证）**：PostgreSQL(5432) ✅ · Core(8787, `db_connected=true`) ✅ · Web(5173, Core/SSE 实时模式) ✅ · OpenClaw Gateway(18789) ✅ · 插件已加载 ✅。
> Core 与 Web 已由用户级 systemd 托管并设置开机自动启动；OpenClaw 缓存的 58 个离线事件已全部回灌数据库。

---

## 一、组件与端口总览

| 组件 | 作用 | 端口 | 启动方式 |
| --- | --- | --- | --- |
| PostgreSQL 16 | Core 的持久化数据库 | `5432` | docker compose **或** apt 本地安装 |
| TraceShield Core | Fastify 审计服务（同步决策 + 异步留痕 + 查询/SSE） | `8787` | `traceshield-core.service` |
| Runtime Method Worker | Core 管理的 Python JSONL 方法引擎（无网络端口） | — | 由 Core 自动管理 |
| TraceShield Web | Runtime Audit 实时控制台 | `5173` | `traceshield-web.service` |
| TraceShield 插件 | OpenClaw 运行时安全门 | — | 已被 OpenClaw 加载（`openclaw-plugin/dist/`） |
| OpenClaw Gateway | OpenClaw WebSocket 网关，加载并驱动插件 | `18789` | `openclaw gateway` |
| OpenClaw Chat | 终端对话 UI，**直接登录** Gateway | — | `openclaw chat` |

> 端口约定：Core 必须在 `8787`（插件的 `core_base_url` 指向它）；Gateway 在 `18789`（`~/.openclaw/openclaw.json` 已配置）。

---

## 二、本机现状（已探测）

- ✅ OpenClaw CLI：已全局安装 `2026.6.6`（`/home/claw/.npm-global/bin/openclaw`），配置已就绪
- ✅ OpenClaw Gateway：已运行在 `18789`，token 鉴权 + DeepSeek key 预置 → **直接登录**
- ⚠️ Docker：CLI 已安装，但当前登录会话访问 `/var/run/docker.sock` 会提示权限不足；PostgreSQL 已经在运行，因此这不影响当前 Core
- ✅ PostgreSQL：`docker compose` 起在 `5432`，容器 `traceshield-postgres` 为 healthy
- ✅ Core：`traceshield-core.service` 持久运行在 `8787`，`db_connected=true`，11/11 表、4 条策略
- ✅ Web：`traceshield-web.service` 持久运行在 `5173`，`web/.env` 已设置 `VITE_USE_MOCK_DATA=false`
- ✅ 插件：`openclaw-plugin/dist/index.js` 已构建并被 Gateway 加载

---

## 三、环境自检（一键核对）

```bash
# Node / OpenClaw 版本
node --version                       # 期望 v18+（本机 v24）
openclaw --version                   # 期望 OpenClaw 2026.6.6

# 端口占用情况
ss -ltn | grep -E ':(5173|5432|8787|18789)\b'

# 持久服务状态
systemctl --user is-active traceshield-core traceshield-web openclaw-gateway

# OpenClaw Gateway 健康 + 插件是否加载
openclaw health
```

---

## 四、启动顺序（总览）

```
1. PostgreSQL (5432) ─► 2. Core (8787) ─┬─► 3. Web (5173)
                                       └─► 4. 插件/Gateway (18789) ─► 5. OpenClaw Chat
```

> OpenClaw Gateway 与 Core **互相独立**：Core 挂了插件会本地降级，Gateway 仍能起。但完整链路（审计落库）需要 Core + PostgreSQL 同时在线。

---

## 五、详细步骤

### 1. 启动 PostgreSQL（5432）

> 本机现状：docker 已装好、镜像加速器已配、容器已在跑。下面是**首次搭建**所需完整步骤。

#### 1-0.（仅一次）安装 Docker + 配置国内镜像加速器

> 本机直连 Docker Hub（registry-1.docker.io）被拒，**必须配镜像加速器**，否则 `docker compose up` 会报 `connection refused`。

```bash
# 安装 Docker Engine + Compose v2（需 sudo）
sudo apt update
sudo apt install -y docker.io docker-compose-v2 containerd
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"     # 免 sudo 用 docker；需重新登录生效（或当前会话用 sg docker -c '...')

# 配置镜像加速器（Docker Hub 直连被拒）
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://dockerproxy.com",
    "https://hub.rat.dev"
  ]
}
JSON
sudo systemctl restart docker
docker info | grep -A6 "Registry Mirrors"   # 确认加速器已加载
```

#### 1-A. 方式 A：docker compose（**本机采用**）

```bash
# 在仓库根目录执行
docker compose up -d postgres          # 首次会经加速器拉 postgres:16
docker compose ps                      # 期望 traceshield-postgres 为 healthy
# 当前会话若提示无权限，用 sg docker -c 'docker compose up -d postgres'
```

账号/密码/库名已在 `docker-compose.yml` 内置，与 `core/.env` 完全一致，无需手动建库。

#### 1-B. 方式 B：apt 本地安装（无 docker 时的备选）

> 需 `sudo`。安装一次即可，开机自启。

```bash
sudo apt update
sudo apt install -y postgresql
sudo systemctl enable --now postgresql

# 建库建用户，与 core/.env 保持一致：
#   用户 traceshield / 密码 traceshield_dev_password / 库 traceshield
sudo -u postgres psql <<'SQL'
CREATE ROLE traceshield WITH LOGIN PASSWORD 'traceshield_dev_password';
CREATE DATABASE traceshield OWNER traceshield;
GRANT ALL PRIVILEGES ON DATABASE traceshield TO traceshield;
SQL

pg_isready -h 127.0.0.1 -p 5432 -U traceshield -d traceshield
```

> 若 `core/.env` 的 `TRACESHIELD_DATABASE_URL` 用了别的用户/密码/库名，请同步修改上面 SQL 和 `.env`。

---

### 2. 启动 TraceShield Core（8787）

```bash
cd core

# 首次：装依赖、生成 .env（本机已完成，可跳过）
npm install
cp .env.example .env        # 确认 TRACESHIELD_DATABASE_URL 指向上面建好的库

# 建表 + 种子策略
npm run db:migrate          # 成功后再继续

# 连通性自检（PostgreSQL 没起会报 ECONNREFUSED 5432）
npm run db:check

# 启动开发服务（前台，监听 http://127.0.0.1:8787）
npm run dev
```

验证 Core 在线：

```bash
curl -s http://127.0.0.1:8787/v1/health || openclaw-plugin 的 demo:core（见步骤 4）
curl -s http://127.0.0.1:8787/v1/method/status
```

> 生产模式可用 `npm run build && npm start`。

#### 推荐：使用持久 systemd 服务

仓库已提供 `deploy/systemd/traceshield-core.service`。当前机器已经 link、enable 并启动：

```bash
cd /home/claw/桌面/traceshield
npm --prefix core run build
systemctl --user link "$PWD/deploy/systemd/traceshield-core.service"   # 首次执行
systemctl --user daemon-reload
systemctl --user enable --now traceshield-core.service

systemctl --user status traceshield-core --no-pager
curl --noproxy '*' -s http://127.0.0.1:8787/v1/health
journalctl --user -u traceshield-core -f
```

> 修改 Core 源码后执行 `npm --prefix core run build && systemctl --user restart traceshield-core`。

---

### 3. 启动 TraceShield Web（5173）

真实 Core/SSE 模式由 `web/.env` 控制：

```env
VITE_TRACESHIELD_CORE_BASE_URL=http://127.0.0.1:8787
VITE_USE_MOCK_DATA=false
```

持久运行使用生产构建，避免 Vite dev watcher 达到系统上限：

```bash
cd /home/claw/桌面/traceshield
npm --prefix web run build
systemctl --user link "$PWD/deploy/systemd/traceshield-web.service"    # 首次执行
systemctl --user daemon-reload
systemctl --user enable --now traceshield-web.service

systemctl --user status traceshield-web --no-pager
curl --noproxy '*' -I http://127.0.0.1:5173/runtime
```

打开：`http://127.0.0.1:5173/runtime`。

修改前端源码后执行：

```bash
npm --prefix web run build
systemctl --user restart traceshield-web
```

开发时需要 HMR 才使用 `cd web && npm run dev`；启动前先停掉持久 Web 服务，避免占用 5173。

---

### 4. 构建 TraceShield 插件（产物供 OpenClaw 加载）

```bash
cd openclaw-plugin
npm install
npm run build               # 输出到 dist/，入口 dist/index.js
```

> 配置里 `~/.openclaw/openclaw.json` 的 `plugins.load.paths` 已指向
> `/home/claw/桌面/traceshield/openclaw-plugin`，OpenClaw 会从其 `dist/index.js` 加载。
> 改了插件源码 → 重新 `npm run build` → 重启 Gateway 生效。

冒烟验证 Core + 插件链路（需 Core 在 8787 在线）：

```bash
cd openclaw-plugin
npm run demo:core
```

---

### 5. OpenClaw 配置说明（**已就绪，直接登录的关键**）

配置文件：`~/.openclaw/openclaw.json`，关键项已预置：

- `gateway.mode=local`，`gateway.auth.mode=token` 且 `gateway.auth.token` **已预置** → 启动即带鉴权，**无需交互登录**
- `gateway.port=18789`，`gateway.bind=loopback`（仅本机）
- `models.providers.deepseek` 的 API key **已预置** → 模型可用
- `plugins.entries.traceshield-security-plugin`：`enabled=true`，`config.core_base_url=http://127.0.0.1:8787`，`mode=demo`，`fallback_enabled=true`
- `plugins.load.paths`：`["/home/claw/桌面/traceshield/openclaw-plugin"]`
- `tools.alsoAllow`：`["traceshield_status"]`

> **"直接登录"含义**：token 与模型 key 都已写进配置，Gateway 一启动即可用、Chat 连接即认证，全程不弹登录/输密。
> 修改配置可用 `openclaw configure`（交互）或 `openclaw config set <key> <value>`（非交互）。

---

### 6. 启动 OpenClaw Gateway（18789）

```bash
# 后台服务方式（推荐，launchd/systemd 托管）
openclaw gateway start

# 或前台调试（看实时日志，Ctrl+C 停止）
openclaw gateway

# 若 18789 已被旧进程占用，强制顶掉：
openclaw gateway --force
```

验证：

```bash
openclaw health            # 期望显示 Gateway 正常、agent:main 在线
openclaw logs              # 实时日志，可确认插件加载/审计决策
```

> 本机当前 Gateway 已在 `18789` 运行；如需重启用 `--force`。

---

### 7. 直接登录并开始对话

```bash
# 直接登录：从 ~/.openclaw/openclaw.json 读取 token，无需任何交互
openclaw chat

# 或打开控制台 UI（带当前 token）
openclaw dashboard

# 非交互发送一条消息做验证（如：调用 traceshield_status 工具）
openclaw chat --message "用 traceshield_status 工具报告当前插件状态"
```

> 如果配置里没带 token、或想显式指定，可加 `--token <gateway token>`。
> Gateway 绑定 `loopback`，本机外访问需改 `gateway.bind`。

---

## 六、常用命令速查

```bash
# Core
cd core
npm run dev              # 前台启动
npm run build            # 持久服务运行 dist 前必须构建
npm run db:migrate       # 建表
npm run db:check         # 连通性检查
npm run seed:demo        # 写入演示数据
npm run smoke            # 冒烟测试

# Web（真实 Core + SSE）
cd ../web
npm run typecheck
npm run build
npm run smoke

# 持久服务
systemctl --user restart traceshield-core traceshield-web
systemctl --user status traceshield-core traceshield-web --no-pager
journalctl --user -u traceshield-core -u traceshield-web -f

# 插件
cd openclaw-plugin
npm run build            # 构建 dist
npm run demo:core        # 冒烟（需 Core 在线）
npm run test             # 单测
npm run typecheck

# OpenClaw
openclaw gateway         # 前台
openclaw gateway start   # 后台服务
openclaw health          # 健康
openclaw logs            # 日志
openclaw chat            # 直接登录聊天
openclaw dashboard       # 控制 UI
openclaw doctor          # 诊断配置/网关/插件/渠道
```

---

## 七、故障排查

| 现象 | 原因 / 处理 |
| --- | --- |
| Core 报 `ECONNREFUSED 127.0.0.1:5432` | PostgreSQL 没起。`sudo systemctl start postgresql`，或按步骤 1-B 安装 |
| Core 报 `password authentication failed` | `core/.env` 的连接串用户/密码/库名与实际不一致；改 `.env` 或重建库 |
| `docker: 未找到命令` | 未装 docker。按步骤 1-0 安装 |
| 拉镜像报 `connection refused` / `registry-1.docker.io` | Docker Hub 直连被拒。按步骤 1-0 配置 `/etc/docker/daemon.json` 镜像加速器后 `sudo systemctl restart docker` |
| `docker compose` 提示无权限 | 当前会话未刷新 docker 组。重新登录，或临时用 `sg docker -c 'docker ...'` |
| `Got permission denied ... /var/run/docker.sock` | 同上，用户不在 docker 组；`sudo usermod -aG docker $USER` 后重登录 |
| OpenClaw 提示 Core 不可用 / `fetch failed` | `systemctl --user restart traceshield-core`，然后 `curl --noproxy '*' http://127.0.0.1:8787/v1/health` |
| 网页一直显示 mock 会话 | 检查 `web/.env` 中 `VITE_USE_MOCK_DATA=false`，重新 `npm run build` 并重启 `traceshield-web` |
| 网页不刷新 OpenClaw 新对话 | 确认顶部为 Core Online / Realtime Connected；检查 Core、Web、Gateway 三个用户服务。纯对话和工具调用现在都会更新 Session |
| Vite 报 `ENOSPC: System limit for number of file watchers reached` | 持久运行不要用 `npm run dev`，改用已经配置的 `traceshield-web.service`（`vite preview`） |
| OpenClaw 离线事件积压 | 查看 `find ~/.traceshield/events -name '*.json' | wc -l`；Core 恢复后 flush worker 会自动回灌并清空 |
| `openclaw chat` 提示需要 token | 配置缺失 token；`openclaw configure` 重配，或 `openclaw chat --token <token>` |
| Gateway `18789` 起不来 | 旧进程占用：`openclaw gateway --force` |
| 插件改了不生效 | `cd openclaw-plugin && npm run build` 后重启 Gateway |
| Core 挂了插件仍能用 | 符合预期：`fallback_enabled=true` 时本地降级（高危阻断、只读放行） |
| 整体诊断 | `openclaw doctor` |

---

## 八、一键启动（PostgreSQL 已就绪后）

```bash
# 构建并启动 Core + Web 持久服务
cd /home/claw/桌面/traceshield
npm --prefix core run db:migrate
npm --prefix core run build
npm --prefix web run build
systemctl --user restart traceshield-core traceshield-web

# Gateway 通常已由 systemd 托管；必要时重启
openclaw gateway restart

# 健康检查
curl --noproxy '*' -s http://127.0.0.1:8787/v1/health
curl --noproxy '*' -I http://127.0.0.1:5173/runtime
openclaw health

# 直接登录聊天；新对话会实时进入 Web Session 列表
openclaw chat
```

## 九、当前持久化架构

```text
OpenClaw Gateway (systemd, 18789)
  └─ TraceShield Plugin
       ├─ sync audit ───────────────► Core (systemd, 8787)
       ├─ async events / disk queue ─► PostgreSQL (5432)
       └─ Core SSE ─────────────────► Web (systemd, 5173)
```

- Core 停机时，插件按 `fallback_enabled=true` 降级并把异步事件写入 `~/.traceshield/events`。
- Core 恢复后，磁盘事件自动回灌；Web 通过 SSE 收到 `trace_event` / `audit_event`。
- Web 初始加载使用 `/v1/audit/sessions`，所以只有对话、没有工具调用的 OpenClaw 会话也会显示。
