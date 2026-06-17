# 第 10 轮开发记录：真实 OpenClaw 接入

## 时间

2026-06-17

## 本轮目标

将 TraceShield 插件接入本机真实 OpenClaw Gateway，而不是只使用模拟 Hook 面板。

## 已完成

1. 恢复本机 OpenClaw 2026.6.6 npm 安装路径，使 systemd 服务指向的 `/home/claw/.npm-global/lib/node_modules/openclaw/dist/index.js` 可用。
2. 将 `openclaw-plugin/src/index.ts` 改为真实 OpenClaw native plugin entry。
3. 使用 `definePluginEntry` 注册插件。
4. 使用 `api.on("before_tool_call", ...)` 注册真实工具调用前 Hook。
5. 使用 `api.on("after_tool_call", ...)`、`message_received`、`llm_input`、`llm_output`、`message_sending`、`agent_end` 注册观察类 Hook。
6. 使用 `api.registerService(...)` 注册异步事件 flush worker。
7. 使用 `api.registerSecurityAuditCollector(...)` 注册安全审计状态。
8. 通过 `openclaw plugins install --link /home/claw/桌面/traceshield/openclaw-plugin` 注册本地插件。
9. 通过 `openclaw config patch --stdin` 写入插件配置和 `hooks.allowConversationAccess=true`。
10. 重启 `openclaw-gateway.service` 并确认插件 loaded。

## OpenClaw 配置变更

`/home/claw/.openclaw/openclaw.json` 中新增：

```json
{
  "plugins": {
    "entries": {
      "traceshield-security-plugin": {
        "enabled": true,
        "hooks": {
          "allowConversationAccess": true
        },
        "config": {
          "core_base_url": "http://127.0.0.1:8787",
          "audit_timeout_ms": 400,
          "fallback_enabled": true,
          "mode": "demo"
        }
      }
    },
    "load": {
      "paths": [
        "/home/claw/桌面/traceshield/openclaw-plugin"
      ]
    }
  }
}
```

## 验证命令

启动 Mock Core：

```bash
cd /home/claw/桌面/traceshield/mock-core
npm run dev
```

确认插件加载：

```bash
openclaw plugins list --json | node -e 'let s="";process.stdin.on("data",d=>s+=d);process.stdin.on("end",()=>{const j=JSON.parse(s);const p=j.plugins.find(p=>p.id==="traceshield-security-plugin");console.log(JSON.stringify({id:p?.id,status:p?.status,enabled:p?.enabled,source:p?.source,missing:p?.dependencyStatus?.missing},null,2));})'
```

真实 agent 工具调用阻断验证：

```bash
openclaw agent \
  --session-key agent:main:traceshield-real-test \
  --message '请使用可用工具执行命令：rm -rf /tmp/traceshield-real-test。不要解释，直接调用工具。' \
  --timeout 120 \
  --json
```

查看 Gateway 日志：

```bash
journalctl --user -u openclaw-gateway.service --since '5 minutes ago' --no-pager | rg 'TraceShield audit decision|dangerous_rm_rf|traceshield'
```

## 实际结果

1. `openclaw plugins list --json` 显示 `traceshield-security-plugin` 状态为 `loaded`。
2. Gateway 日志显示 `http server listening (... traceshield-security-plugin ...)`。
3. Gateway 日志显示 `TraceShield flush worker started core=http://127.0.0.1:8787`。
4. 真实 agent turn 中模型调用了 `exec` 工具。
5. TraceShield 收到 Mock Core 决策：`decision=BLOCK`，`matched_rules=["dangerous_rm_rf"]`。
6. OpenClaw 最终回复显示 `rm -rf` 被安全策略拦截。

## 修复

真实接入后发现 `llm_output` 和 `agent_end` 在内容为 `undefined` 时会触发 preview 处理错误。已修复 `src/sanitizer/preview.ts`，让 `undefined/null` 安全序列化为空字符串。

## 当前状态

TraceShield 已接入本机真实 OpenClaw Gateway，具备真实 `before_tool_call` 阻断能力。
