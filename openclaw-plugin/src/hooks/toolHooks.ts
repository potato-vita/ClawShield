import type { AuditClient } from "../client/auditClient.js";
import type { Logger } from "../logger.js";
import { mapAuditDecision } from "../policy/decisionMapper.js";
import { evaluateFallbackPolicy } from "../policy/fallbackPolicy.js";
import { normalizeToolCall, buildAuditRequest } from "../events/normalizeToolCall.js";
import { normalizeToolResult } from "../events/normalizeToolResult.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type {
  OpenClawToolDecisionResult,
  RawToolCallHookInput,
  RawToolResultHookInput,
} from "../types/hook.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import { createId } from "../utils/id.js";

export interface RegisterToolHooksOptions {
  api: unknown;
  queue: MemoryQueue<TraceEvent>;
  config: PluginConfig;
  logger: Logger;
  auditClient: AuditClient;
  on: (
    api: unknown,
    name: string,
    handler: (event: unknown, ctx: Record<string, unknown>) => unknown,
    opts?: Record<string, unknown>,
  ) => void;
}

/**
 * 注册工具调用 Hook：before_tool_call 同步审计 + after_tool_call 异步留痕。
 * Core 不可用时自动切到本地降级策略。
 */
export function registerToolHooks(options: RegisterToolHooksOptions): void {
  const { api, queue, config, logger, auditClient, on } = options;

  on(
    api,
    "before_tool_call",
    async (event: unknown, ctx: Record<string, unknown>) => {
      const rawInput = toRawToolCallInput(event, ctx);
      queue.enqueue(normalizeToolCall(rawInput, config));
      const auditRequest = buildAuditRequest(rawInput);

      try {
        const decision = await auditClient.auditToolCall(auditRequest);
        logger.info("TraceShield audit decision received", {
          decision: decision.decision,
          risk_level: decision.risk_level,
          matched_rules: decision.matched_rules,
        });
        return toOpenClawBeforeToolResult(mapAuditDecision(decision));
      } catch (error) {
        logger.warn("TraceShield audit request failed; using fallback policy", {
          reason: error instanceof Error ? error.message : String(error),
        });

        if (!config.fallback_enabled) {
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

        return toOpenClawBeforeToolResult(mapAuditDecision(fallbackDecision));
      }
    },
    { priority: 100, timeoutMs: config.audit_timeout_ms + 200 },
  );

  on(
    api,
    "after_tool_call",
    (event: unknown, ctx: Record<string, unknown>) => {
      queue.enqueue(normalizeToolResult(toRawToolResultInput(event, ctx), config));
    },
    { priority: 80, timeoutMs: 2_000 },
  );
}

function toRawToolCallInput(event: unknown, ctx: Record<string, unknown>): RawToolCallHookInput {
  const input = asRecord(event);
  const context = asRecord(ctx);
  const raw: RawToolCallHookInput = {
    tool_name: readString(input.toolName) ?? "unknown",
    params: asRecord(input.params),
    metadata: { derivedPaths: input.derivedPaths, context },
  };
  assignOptionalString(
    raw,
    "session_id",
    readString(context.sessionId) ?? readString(context.sessionKey),
  );
  assignOptionalString(raw, "run_id", readString(input.runId) ?? readString(context.runId));
  assignOptionalString(raw, "trace_id", readTraceId(context.trace) ?? readString(input.traceId));
  assignOptionalString(
    raw,
    "workspace_root",
    readString(context.workspaceDir) ?? readString(context.cwd),
  );
  assignOptionalString(raw, "tool_call_id", readString(input.toolCallId));
  assignOptionalString(
    raw,
    "tool_kind",
    readString(input.toolKind) ?? readString(context.toolKind),
  );
  return raw;
}

function toRawToolResultInput(
  event: unknown,
  ctx: Record<string, unknown>,
): RawToolResultHookInput {
  const input = asRecord(event);
  const raw: RawToolResultHookInput = toRawToolCallInput(event, ctx);
  raw.result = input.result;
  raw.error = input.error;
  if (typeof input.durationMs === "number") {
    raw.duration_ms = input.durationMs;
  }
  return raw;
}

function toOpenClawBeforeToolResult(
  result: OpenClawToolDecisionResult,
): Record<string, unknown> | undefined {
  if (result.block) {
    return {
      block: true,
      blockReason: result.blockReason,
    };
  }

  if (result.requireApproval) {
    return {
      requireApproval: {
        title: result.requireApproval.title,
        description: result.requireApproval.description,
        severity: result.auditDecision?.risk_level === "critical" ? "critical" : "warning",
        timeoutMs: result.requireApproval.timeoutMs,
        timeoutBehavior: result.requireApproval.defaultAction === "ALLOW" ? "allow" : "deny",
      },
    };
  }

  if (result.modifiedParams) {
    return { params: result.modifiedParams };
  }

  return undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function readTraceId(value: unknown): string | undefined {
  const trace = asRecord(value);
  return readString(trace.traceId) ?? readString(trace.id);
}

function assignOptionalString<T extends object>(
  target: T,
  key: keyof T,
  value: string | undefined,
): void {
  if (value !== undefined) {
    (target as Record<string, unknown>)[String(key)] = value;
  }
}
