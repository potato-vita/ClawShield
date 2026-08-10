# TraceShield 完整启动手册

本手册是当前唯一的启动操作入口，面向人和自动化 Agent。它覆盖 PostgreSQL、TraceShield Core、方法引擎、Web、CloudWeGo Eino Assistant、TraceShield OpenClaw 插件和 OpenClaw Gateway。

除非明确处于首次安装或调试阶段，优先使用本文的“日常完整启动”流程。不要同时运行 systemd 服务和同端口的 `npm run dev`。

## 目标状态

完成后应有以下服务：

| 组件 | 期望状态 | 端口 |
| --- | --- | --- |
| PostgreSQL | Docker 容器 `healthy` | `5432` |
| Eino Assistant | `traceshield-assistant.service` 为 `active` | `8790`，仅回环地址 |
| TraceShield Core | `traceshield-core.service` 为 `active` | `8787` |
| TraceShield Web | `traceshield-web.service` 为 `active` | `5173` |
| 公共只读网关 | `traceshield-public-gateway.service` 为 `active` | `127.0.0.1:5180` |
| Cloudflare Quick Tunnel | `traceshield-public-tunnel.service` 为 `active` | 临时 HTTPS URL |
| OpenClaw Gateway | `openclaw-gateway.service` 为 `active` | `18789` |
| OpenClaw Control UI HTTPS Tunnel | `traceshield-openclaw-public-tunnel.service` 为 `active` | 临时 HTTPS URL |
| TraceShield 插件 | Gateway 日志出现 `TraceShield Security Plugin registered` | 无单独端口 |
| Method Worker | Core 的 `/v1/method/status` 返回 `status: ok` | 无单独端口 |

Assistant 的调用链是 `Web /assistant → Core /v1/assistant/* → Eino :8790 → DeepSeek`。它只解释已提供的摘要上下文，不注册工具，也不参与 `ALLOW / WARN / ASK / BLOCK` 的实际裁决。

## 安全规则

- 不读取、打印、粘贴或提交 `~/.openclaw/openclaw.json` 中的 Gateway token、模型 API key。
- 不向聊天、日志、版本库或截图写入任何真实凭据。
- 在局域网模式下，Web、Core 和 Gateway 对网络可见。只允许受信任主机访问，并用防火墙或私网隔离。
- 公网临时入口只转发 Web 和 Core 的只读请求；它不公开 PostgreSQL、OpenClaw Gateway、Core 写接口或 Assistant 对话接口。
- 不启动 `mock-core/`，除非专门做旧版演示；它会与真实 Core 争用 `8787`。

## 日常完整启动

在仓库根目录执行。该流程可重复运行。

```bash
cd /home/claw/桌面/traceshield

# 1. 启动并等待 PostgreSQL 健康
docker compose up -d --wait postgres

# 2. 应用迁移，测试并构建 Eino Assistant、Core、Web 与插件
npm --prefix core run db:migrate
(cd assistant-eino && go test ./... && mkdir -p bin && go build -o bin/traceshield-assistant ./cmd/server)
npm --prefix core run build
npm --prefix web run build
npm --prefix openclaw-plugin run build

# 3. 重启持久服务
systemctl --user daemon-reload
systemctl --user restart traceshield-assistant
systemctl --user restart traceshield-core traceshield-web openclaw-gateway
```

Core 启动时会自动拉起 Python Method Worker。不要额外单独启动该 Worker。

## 启动后验证

运行以下命令。每一步都应成功；某项失败时先按后文“故障定位”处理，不要盲目反复重启全部服务。

```bash
cd /home/claw/桌面/traceshield

# 数据库、用户服务与本地 HTTP 健康检查
docker compose ps postgres
systemctl --user is-active traceshield-assistant traceshield-core traceshield-web openclaw-gateway
curl --noproxy '*' --fail --silent http://127.0.0.1:8790/health
curl --noproxy '*' --fail --silent http://127.0.0.1:8787/v1/health
curl --noproxy '*' --fail --silent http://127.0.0.1:8787/v1/assistant/health
curl --noproxy '*' --fail --silent --output /dev/null http://127.0.0.1:5173/runtime

# 方法引擎、Gateway 和已加载插件
npm --prefix core run method:health
openclaw health
journalctl --user -u openclaw-gateway -n 80 --no-pager | grep -F 'TraceShield Security Plugin registered'
```

预期结果：PostgreSQL 为 `healthy`；四个用户服务均为 `active`；Assistant 直连和 Core 代理 health 均返回 `ok: true`、`framework: "cloudwego-eino"`、`provider: "deepseek"`、`configured: true`；Core health 中的 `db_connected` 为 `true`；Web 返回 HTTP `200`；方法引擎返回 `status: ok`；Gateway 健康且日志确认插件已注册。

可选地用一次短请求验证完整流式链路：

```bash
curl --noproxy '*' --fail-with-body -N http://127.0.0.1:8787/v1/assistant/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"请只回复：EINO_CONNECTED","history":[],"context":{"source":"runbook-check"}}'
```

响应应依次包含 `event: start`、一个或多个 `event: delta` 和 `event: done`。浏览器页面通过同一个 Core 代理接口工作。

## 从主机访问虚拟机

先取得虚拟机的 LAN 地址：

```bash
VM_IP="$(hostname -I | awk '{print $1}')"
printf 'TraceShield Web: http://%s:5173/runtime\n' "$VM_IP"
printf 'Assistant UI:    http://%s:5173/assistant\n' "$VM_IP"
printf 'TraceShield Core: http://%s:8787/v1/health\n' "$VM_IP"
```

主机浏览器通常应访问：

```text
http://<VM_IP>:5173/runtime
http://<VM_IP>:5173/assistant
```

`8790` 默认只监听虚拟机回环地址，不需要也不应从主机浏览器直连。打开 `/assistant` 后，先在左侧选择演示案例或直接输入问题；回复会逐段流式显示。生成过程中可停止，连接失败后可重试。页面显示的 Eino/DeepSeek 状态来自 Core 的 `/v1/assistant/health`。

不要从主机浏览器使用 `http://<VM_IP>:18789` 登录 OpenClaw Control UI。这个 HTTP 地址虽然能加载页面，但浏览器不能建立设备身份，Gateway 会拒绝 WebSocket 连接。请按“OpenClaw Control UI HTTPS 访问”使用 HTTPS 隧道。

若 Gateway 首次需要从主机浏览器访问，显式配置 LAN 绑定与允许来源，然后重启 Gateway：

```bash
VM_IP="$(hostname -I | awk '{print $1}')"
openclaw config set gateway.bind lan
openclaw config set gateway.controlUi.allowedOrigins "[\"http://localhost:18789\",\"http://127.0.0.1:18789\",\"http://${VM_IP}:18789\"]"
systemctl --user restart openclaw-gateway
```

虚拟机 DHCP 地址变化后，需要用新地址重新执行这段配置。若访问失败，也检查虚拟机网络模式和主机防火墙。

## 公网临时访问（Cloudflare Quick Tunnel）

公共入口通过 Cloudflare 的出站 HTTPS 隧道访问本机回环地址 `127.0.0.1:5180`，因此不需要 VMware 桥接、路由器端口转发或向公网开放 `5173`、`8787`、`8790`、`18789`、`5432`。

第一次启用时，链接并启动两个用户服务：

```bash
cd /home/claw/桌面/traceshield
systemctl --user link "$PWD/deploy/systemd/traceshield-public-gateway.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-public-tunnel.service"
systemctl --user daemon-reload
systemctl --user enable --now traceshield-public-gateway traceshield-public-tunnel
```

查看当前分配的公网 HTTPS 地址：

```bash
journalctl --user -u traceshield-public-tunnel --no-pager \
  | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' \
  | tail -n 1
```

将输出的地址加上 `/runtime` 后提供给访问者。也可使用该地址的 `/overview`、`/sessions`、`/tool-calls` 等 Web 路由。

```bash
PUBLIC_URL="$(journalctl --user -u traceshield-public-tunnel --no-pager | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -n 1)"
curl --noproxy '*' --fail --silent "$PUBLIC_URL/v1/health"
```

公共入口是**只读展示模式**：

- Web 静态页面和 Core 的 `GET`、`HEAD`、`OPTIONS` `/v1/*` 请求可通过。
- `POST`、`PATCH` 等写请求返回 `403`，因此不能从公网修改策略或执行审批写入。
- Eino Assistant 的流式对话使用 `POST`，默认不会经此入口暴露，以避免公开模型调用和 API 成本。
- OpenClaw Gateway、PostgreSQL、Eino 的 `8790` 端口和 Core 原始端口不通过该隧道发布。
- Cloudflare Quick Tunnel 会缓冲本项目的长 SSE 响应，因此 HTTPS 公网页面每 10 秒刷新一次只读审计数据；局域网 HTTP 页面仍使用原生 SSE 实时流。

停止公网入口：

```bash
systemctl --user stop traceshield-public-tunnel traceshield-public-gateway
```

Quick Tunnel 适合演示、答辩和临时共享：地址随机、服务重启后可能改变，并且没有生产可用性保证。需要固定域名、登录保护或长期公网部署时，使用自己的 Cloudflare 域名创建 Named Tunnel，并在 Cloudflare Access 中为该域名配置身份访问控制；不要把临时公开的只读入口直接当作生产管理面。

### OpenClaw Control UI HTTPS 访问

OpenClaw Control UI 在非本机浏览器中需要 HTTPS 安全上下文来生成设备身份。仓库提供独立隧道，不与 TraceShield 的只读展示入口混用：

```bash
cd /home/claw/桌面/traceshield
systemctl --user link "$PWD/deploy/systemd/traceshield-openclaw-public-tunnel.service"
systemctl --user daemon-reload
systemctl --user enable --now traceshield-openclaw-public-tunnel

journalctl --user -u traceshield-openclaw-public-tunnel --no-pager \
  | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' \
  | tail -n 1
```

在主机浏览器打开输出的 HTTPS 地址。Control UI 会自动使用同源 `wss://` WebSocket；输入 Gateway token 后点击连接。首次从某个浏览器连接时，Gateway 会创建设备配对请求。仅在确认该请求来自自己的浏览器后，在虚拟机执行：

```bash
openclaw devices list
openclaw devices approve <request-id>
```

每次此 Quick Tunnel 重启后都可能生成新 URL。新地址需要加入 `gateway.controlUi.allowedOrigins` 后重启 Gateway 才能连接：

```bash
VM_IP="$(hostname -I | awk '{print $1}')"
OPENCLAW_PUBLIC_URL="$(journalctl --user -u traceshield-openclaw-public-tunnel --no-pager | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -n 1)"
openclaw config set gateway.controlUi.allowedOrigins "[\"http://localhost:18789\",\"http://127.0.0.1:18789\",\"http://${VM_IP}:18789\",\"${OPENCLAW_PUBLIC_URL}\"]"
systemctl --user restart openclaw-gateway
```

该临时 HTTPS 隧道会公开 Gateway Control UI 的登录页面，但 Gateway token 和已批准设备仍是必需条件。长期使用应改为 Cloudflare Named Tunnel 与 Cloudflare Access，而不是依赖随机的 Quick Tunnel 地址。

## 首次或迁移到新机器时

以下步骤只在依赖、服务或本地配置不存在时执行。日常启动不需要重复安装。

### 1. 准备依赖和环境文件

需要 Node.js 18+、npm、Docker Compose、Python 3.10+、Go 1.22+、OpenClaw CLI 和用户级 systemd。进入仓库后：

```bash
cd /home/claw/桌面/traceshield
npm --prefix core install
npm --prefix web install
npm --prefix openclaw-plugin install
(cd assistant-eino && go mod download)

test -f core/.env || cp core/.env.example core/.env
test -f web/.env || cp web/.env.example web/.env
```

在启动前，确认 `core/.env` 的数据库连接指向本机 PostgreSQL，并准备仓库根目录的 `api-key` 文件供 Assistant 服务读取。该文件只需包含 DeepSeek API key 本身，不要在命令参数或文档中展开其内容。

方法引擎默认需要以下虚拟环境；缺失时创建：

```bash
python3 -m venv core/method-engine/.venv
core/method-engine/.venv/bin/pip install -e 'core/method-engine[dev]'
```

### 2. 安装 Assistant、Core 与 Web 的用户服务

仓库提供的 unit 文件当前将工作目录固定为 `/home/claw/桌面/traceshield`。如果仓库放在其他路径，先同步修改服务文件中的 `WorkingDirectory`、Assistant 的 `ExecStart` 和 `TRACESHIELD_ASSISTANT_API_KEY_FILE` 绝对路径，再执行：

```bash
cd /home/claw/桌面/traceshield
systemctl --user link "$PWD/deploy/systemd/traceshield-core.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-web.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-assistant.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-public-gateway.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-public-tunnel.service"
systemctl --user link "$PWD/deploy/systemd/traceshield-openclaw-public-tunnel.service"
systemctl --user daemon-reload
systemctl --user enable traceshield-assistant traceshield-core traceshield-web traceshield-public-gateway traceshield-public-tunnel traceshield-openclaw-public-tunnel
```

服务单元默认让 Assistant 从仓库根目录的 `api-key` 读取凭据，并监听 `127.0.0.1:8790`。在首次启动前先构建可执行文件：

```bash
(cd assistant-eino && mkdir -p bin && go build -o bin/traceshield-assistant ./cmd/server)
systemctl --user start traceshield-assistant
```

### 3. 配置 OpenClaw 加载插件

在 `~/.openclaw/openclaw.json` 中完成以下本地配置，不要提交该文件：

- Gateway 使用 token 鉴权，端口为 `18789`。
- `plugins.load.paths` 包含插件绝对路径，例如 `/home/claw/桌面/traceshield/openclaw-plugin`。
- `plugins.entries.traceshield-security-plugin.enabled` 为 `true`。
- 插件配置中的 `core_base_url` 为 `http://127.0.0.1:8787`。
- `fallback_enabled` 保持 `true`。
- `tools.alsoAllow` 包含 `traceshield_status`。

已有 OpenClaw 用户服务时，直接启动即可：

```bash
systemctl --user enable --now openclaw-gateway
```

没有该用户服务时，使用 OpenClaw CLI 的服务启动方式：

```bash
openclaw gateway start
```

随后返回“日常完整启动”步骤构建插件并重启 Gateway。

## 修改后的重启规则

| 修改内容 | 必做操作 |
| --- | --- |
| `core/src/`、Core 配置或方法引擎代码 | `npm --prefix core run build && systemctl --user restart traceshield-core` |
| `assistant-eino/` Go 代码或模型配置 | `(cd assistant-eino && go test ./... && go build -o bin/traceshield-assistant ./cmd/server) && systemctl --user restart traceshield-assistant` |
| `web/src/` 或 Web `.env` | `npm --prefix web run build && systemctl --user restart traceshield-web` |
| `openclaw-plugin/src/` 或插件配置 | `npm --prefix openclaw-plugin run build && systemctl --user restart openclaw-gateway` |
| 数据库迁移 | `npm --prefix core run db:migrate && systemctl --user restart traceshield-core` |
| Gateway LAN 绑定或允许来源 | `systemctl --user restart openclaw-gateway` |

## 开发模式

开发时先停掉会占用相同端口的持久服务：

```bash
systemctl --user stop traceshield-assistant traceshield-core traceshield-web
```

然后分别前台运行：

```bash
cd core && npm run dev
cd web && npm run dev
(cd assistant-eino && TRACESHIELD_ASSISTANT_API_KEY_FILE="$PWD/../api-key" go run ./cmd/server)
```

开发完成后，重新构建并按“日常完整启动”恢复 systemd 服务。Gateway 调试可用 `openclaw gateway` 前台运行，但不要与 `openclaw-gateway.service` 同时运行。

## 推荐测试顺序

```bash
cd /home/claw/桌面/traceshield

npm --prefix core run smoke
npm --prefix core run method:test
npm --prefix core run method:health
(cd assistant-eino && go test ./...)
npm --prefix openclaw-plugin run typecheck
npm --prefix openclaw-plugin run test
npm --prefix openclaw-plugin run demo:core
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix web run smoke
```

`demo:core` 验证插件对运行中真实 Core 的策略联调；它不是浏览器控制台或模型提供商的端到端替代测试。

## 故障定位

| 现象 | 先执行 | 常见原因与处理 |
| --- | --- | --- |
| Core 无法连接数据库 | `docker compose ps postgres` | PostgreSQL 未 healthy；重新执行 `docker compose up -d --wait postgres`。 |
| Core health 的 `db_connected` 为 `false` | `npm --prefix core run db:check` | `core/.env` 中连接串与数据库不一致，或迁移未执行。 |
| Core 启动但方法引擎不可用 | `npm --prefix core run method:health` | `core/method-engine/.venv` 缺失或依赖未安装；按首次步骤创建虚拟环境。 |
| Assistant 服务无法启动 | `journalctl --user -u traceshield-assistant -n 120 --no-pager` | 可执行文件尚未构建、根目录 `api-key` 不存在或为空、Go 依赖未下载；按首次步骤重新准备并构建。 |
| Assistant 直连 health 失败 | `curl --noproxy '*' http://127.0.0.1:8790/health` | 服务未启动或 `8790` 被占用；检查 `systemctl --user status traceshield-assistant` 和日志。 |
| Core 的 Assistant health 返回 503 | `curl --noproxy '*' http://127.0.0.1:8787/v1/assistant/health` | 先确认 Eino 的直连 health；再检查 Core 的 `TRACESHIELD_ASSISTANT_BASE_URL` 是否为 `http://127.0.0.1:8790`。 |
| `/assistant` 能打开但不返回内容 | `curl --noproxy '*' -N http://127.0.0.1:8787/v1/assistant/chat/stream -H 'Content-Type: application/json' -d '{"message":"ping"}'` | 查看 Eino 与 Core 日志；常见原因是模型接口不可达、额度/限流、模型名不匹配或 Core 代理超时。 |
| Web 无数据或显示 mock | `cat web/.env` | 将 `VITE_USE_MOCK_DATA` 设为 `false`，构建并重启 Web。 |
| Web 页面能打开但 Core 请求失败 | `curl http://127.0.0.1:8787/v1/health` | 先恢复 Core；局域网访问时确认浏览器可以到达 `<VM_IP>:8787`。 |
| OpenClaw UI 页面能打开但无法连接 | `openclaw health` | 检查 Gateway token、`gateway.bind=lan` 和 `gateway.controlUi.allowedOrigins`。 |
| Gateway 未加载插件 | `journalctl --user -u openclaw-gateway -n 120 --no-pager` | 重新构建插件，确认 `plugins.load.paths` 的绝对路径，然后重启 Gateway。 |
| 插件显示 Core 不可用 | `curl http://127.0.0.1:8787/v1/health` | 插件同机调用应保持 `core_base_url=http://127.0.0.1:8787`。 |
| 端口已占用 | `ss -ltnp | grep -E ':(5173|8787|8790|18789)\b'` | 停止重复的开发进程或对应 systemd 服务后再启动。 |

## 停止服务

```bash
systemctl --user stop traceshield-assistant traceshield-core traceshield-web openclaw-gateway
docker compose stop postgres
```

仅停止 Assistant 时，审计裁决、事件入库、策略中心和 OpenClaw 插件仍正常工作，只有 `/assistant` 对话不可用。停止 Core 时，插件仍可按本地降级策略工作；但完整审计入库、SSE 和控制台实时数据会不可用。
