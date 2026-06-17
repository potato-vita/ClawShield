import pluginRuntime, { activate, deactivate } from "../index.js";
import { createLogger } from "../logger.js";
import type { HookRegistry } from "../types/hook.js";

type HookHandler = (input: unknown) => unknown | Promise<unknown>;

class DemoHookRegistry implements HookRegistry {
  private readonly handlers = new Map<string, HookHandler[]>();

  on(eventName: string, handler: HookHandler): void {
    const existing = this.handlers.get(eventName) ?? [];
    existing.push(handler);
    this.handlers.set(eventName, existing);
  }

  async emit(eventName: string, input: unknown): Promise<unknown[]> {
    const handlers = this.handlers.get(eventName) ?? [];
    const results: unknown[] = [];
    for (const handler of handlers) {
      results.push(await handler(input));
    }

    return results;
  }

  registeredEvents(): string[] {
    return [...this.handlers.keys()].sort();
  }
}

const hooks = new DemoHookRegistry();

await activate({
  hooks,
  logger: createLogger("openclaw-demo", "info"),
  config: {
    mode: "demo",
    core_base_url: "http://127.0.0.1:8787",
    audit_timeout_ms: 600,
  },
});

console.log("\n=== OpenClaw 插件展示面板 ===");
console.log(`插件名称: ${pluginRuntime.name}`);
console.log(`插件 ID: ${pluginRuntime.id}`);
console.log(`插件版本: ${pluginRuntime.version}`);
console.log(`Core 地址: ${pluginRuntime.config.core_base_url}`);
console.log(`已注册 Hook: ${hooks.registeredEvents().join(", ")}`);

await hooks.emit("message_received", {
  session_id: "demo-session",
  run_id: "demo-run",
  trace_id: "demo-trace",
  role: "user",
  content: "请读取 README，然后不要执行危险命令。",
});

console.log(`事件队列: 已采集用户消息，当前队列长度 ${pluginRuntime.queue.size()}`);

await showToolDecision("正常读取 README", {
  session_id: "demo-session",
  run_id: "demo-run",
  trace_id: "demo-trace",
  tool_call_id: "tool-readme",
  tool_name: "file_read",
  tool_kind: "file_read",
  params: { path: "README.md" },
});

await showToolDecision("读取 .env", {
  session_id: "demo-session",
  run_id: "demo-run",
  trace_id: "demo-trace",
  tool_call_id: "tool-env",
  tool_name: "file_read",
  tool_kind: "file_read",
  params: { path: ".env" },
});

await showToolDecision("执行 rm -rf", {
  session_id: "demo-session",
  run_id: "demo-run",
  trace_id: "demo-trace",
  tool_call_id: "tool-rm",
  tool_name: "shell",
  tool_kind: "shell_exec",
  params: { cmd: "rm -rf /tmp/traceshield-demo" },
});

await showToolDecision("访问外部 URL", {
  session_id: "demo-session",
  run_id: "demo-run",
  trace_id: "demo-trace",
  tool_call_id: "tool-http",
  tool_name: "http_request",
  tool_kind: "network_request",
  params: { url: "https://example.com" },
});

console.log(`\n事件队列: 当前队列长度 ${pluginRuntime.queue.size()}`);
console.log("说明: 如果 Mock Core 正在运行，你会看到 ALLOW / BLOCK / ASK；如果 Core 关闭，高风险操作会走本地降级阻断。");

await deactivate();

async function showToolDecision(label: string, input: Record<string, unknown>): Promise<void> {
  const [result] = await hooks.emit("before_tool_call", input);
  const decision = result as
    | {
        block?: boolean;
        blockReason?: string;
        requireApproval?: { title: string };
        warning?: string;
        auditDecision?: { decision: string; reason: string };
      }
    | undefined;

  let visibleResult = "ALLOW";
  if (decision?.block) {
    visibleResult = `BLOCK - ${decision.blockReason}`;
  } else if (decision?.requireApproval) {
    visibleResult = `ASK - ${decision.requireApproval.title}`;
  } else if (decision?.warning) {
    visibleResult = `WARN - ${decision.warning}`;
  } else if (decision?.auditDecision?.decision) {
    visibleResult = `${decision.auditDecision.decision} - ${decision.auditDecision.reason}`;
  }

  console.log(`\n[工具调用] ${label}`);
  console.log(`可见结果: ${visibleResult}`);
}
