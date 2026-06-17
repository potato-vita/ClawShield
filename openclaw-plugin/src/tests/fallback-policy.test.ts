import { describe, expect, it } from "vitest";
import { evaluateFallbackPolicy } from "../policy/fallbackPolicy.js";
import { LocalPolicyCache } from "../policy/localPolicyCache.js";
import { defaultPluginConfig } from "../types/config.js";
import type { AuditRequest } from "../types/event.js";

describe("fallback policy", () => {
  it("blocks high-risk tools when Core is unavailable", () => {
    const decision = evaluateFallbackPolicy(request({ tool_kind: "shell_exec" }), defaultPluginConfig);
    expect(decision.decision).toBe("BLOCK");
    expect(decision.fallback_used).toBe(true);
  });

  it("blocks sensitive reads", () => {
    const decision = evaluateFallbackPolicy(
      request({ tool_kind: "file_read", resource_hint: ".env" }),
      defaultPluginConfig,
    );
    expect(decision.decision).toBe("BLOCK");
  });

  it("allows cached readonly tools", () => {
    const cache = new LocalPolicyCache();
    const auditRequest = request({ tool_kind: "file_read", resource_hint: "README.md" });
    cache.allow(auditRequest);
    const decision = evaluateFallbackPolicy(auditRequest, defaultPluginConfig, cache);
    expect(decision.decision).toBe("ALLOW");
  });

  it("asks for unknown uncached tools", () => {
    const decision = evaluateFallbackPolicy(request({ tool_kind: "unknown" }), defaultPluginConfig);
    expect(decision.decision).toBe("ASK");
  });
});

function request(overrides: Partial<AuditRequest>): AuditRequest {
  return {
    request_id: "req1",
    schema_version: "v1",
    session_id: "s1",
    run_id: "r1",
    trace_id: "t1",
    tool_call_id: "tc1",
    tool_name: "tool",
    tool_kind: "file_read",
    raw_params: {},
    param_summary: {},
    context: {},
    ...overrides,
  };
}
