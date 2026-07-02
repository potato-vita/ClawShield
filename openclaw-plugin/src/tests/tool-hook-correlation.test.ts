import { describe, expect, it } from "vitest";
import { registerToolHooks } from "../hooks/toolHooks.js";
import { MemoryQueue } from "../queue/memoryQueue.js";
import { RunContextRegistry } from "../runtime/runContextRegistry.js";
import { defaultPluginConfig } from "../types/config.js";
import type { AuditRequest, TraceEvent } from "../types/event.js";

describe("tool hook correlation", () => {
  it("uses one tool_call_id and step_seq for sync audit and before/after events", async () => {
    const handlers = new Map<string, (event: unknown, ctx: Record<string, unknown>) => unknown>();
    const requests: AuditRequest[] = [];
    const observations: Record<string, unknown>[] = [];
    const queue = new MemoryQueue<TraceEvent>();
    registerToolHooks({
      api: {},
      queue,
      config: defaultPluginConfig,
      runContextRegistry: new RunContextRegistry(),
      observationClient: { detect: async (payload: Record<string, unknown>) => { observations.push(payload); } } as never,
      auditClient: {
        auditToolCall: async (request: AuditRequest) => {
          requests.push(request);
          return { decision: "ALLOW", risk_level: "low", reason: "ok", matched_rules: [] };
        },
      } as never,
      logger: { debug() {}, info() {}, warn() {}, error() {} },
      on: (_api, name, handler) => handlers.set(name, handler),
    });

    const ctx = { sessionKey: "session-a", workspaceDir: "/workspace" };
    await handlers.get("before_tool_call")?.({ toolName: "read_file", params: { path: "README.md" } }, ctx);
    handlers.get("after_tool_call")?.(
      { toolName: "read_file", params: { path: "README.md" }, result: "ok" },
      ctx,
    );

    const events = queue.drain().map((item) => item.value);
    const before = events.find((event) => event.type === "before_tool_call");
    const after = events.find((event) => event.type === "after_tool_call");
    expect(requests).toHaveLength(1);
    expect(before?.payload.tool_call_id).toBe(requests[0]?.tool_call_id);
    expect(after?.payload.tool_call_id).toBe(requests[0]?.tool_call_id);
    expect(before?.payload.step_seq).toBe(1);
    expect(after?.payload.step_seq).toBe(1);
    expect(requests[0]?.step_seq).toBe(1);
    expect(observations[0]).toMatchObject({
      tool_call_id: requests[0]?.tool_call_id,
      step_seq: 1,
      observation: "ok",
    });
    expect(after?.payload).not.toHaveProperty("transient_observation");
  });
});
