import type { AuditClient } from "../client/auditClient.js";
import { mapAuditDecision } from "../policy/decisionMapper.js";
import { evaluateFallbackPolicy } from "../policy/fallbackPolicy.js";
import { normalizeToolCall, buildAuditRequest } from "../events/normalizeToolCall.js";
import { normalizeToolResult } from "../events/normalizeToolResult.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type {
  HookRegistry,
  OpenClawToolDecisionResult,
  RawToolCallHookInput,
  RawToolResultHookInput,
} from "../types/hook.js";
import type { Logger } from "../logger.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import { createId } from "../utils/id.js";

export interface ToolHookOptions {
  hooks: HookRegistry;
  queue: MemoryQueue<TraceEvent>;
  config: PluginConfig;
  logger: Logger;
  auditClient?: AuditClient;
  auditMode?: "observe" | "enforce";
}

export function registerToolHooks(options: ToolHookOptions): void {
  const { hooks, queue, config, logger, auditClient, auditMode = "observe" } = options;

  hooks.on("before_tool_call", async (input) => {
    const rawInput = input as RawToolCallHookInput;
    queue.enqueue(normalizeToolCall(rawInput, config));

    if (!auditClient) {
      return undefined;
    }

    const auditRequest = buildAuditRequest(rawInput);
    try {
      const decision = await auditClient.auditToolCall(auditRequest);
      logger.info("TraceShield audit decision received", {
        decision: decision.decision,
        risk_level: decision.risk_level,
        matched_rules: decision.matched_rules,
      });

      return auditMode === "enforce" ? mapAuditDecision(decision) : undefined;
    } catch (error) {
      logger.warn("TraceShield audit request failed", {
        reason: error instanceof Error ? error.message : String(error),
      });

      if (auditMode !== "enforce" || !config.fallback_enabled) {
        return undefined;
      }

      const fallbackDecision = evaluateFallbackPolicy(auditRequest, config);
      queue.enqueue({
        event_id: createId("evt"),
        schema_version: "v1",
        type: "fallback_decision",
        timestamp: Date.now(),
        plugin_id: config.plugin_id,
        ...(config.gateway_id ? { gateway_id: config.gateway_id } : {}),
        session_id: auditRequest.session_id,
        run_id: auditRequest.run_id,
        trace_id: auditRequest.trace_id,
        mode: "async",
        payload: { ...fallbackDecision },
      });

      return mapAuditDecision(fallbackDecision) satisfies OpenClawToolDecisionResult;
    }
  });

  hooks.on("after_tool_call", (input) => {
    queue.enqueue(normalizeToolResult(input as RawToolResultHookInput, config));
  });
}
