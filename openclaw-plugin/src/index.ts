import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { AuditClient } from "./client/auditClient.js";
import { EventClient } from "./client/eventClient.js";
import { loadConfig } from "./config.js";
import { buildAuditRequest } from "./events/normalizeToolCall.js";
import { normalizeToolCall } from "./events/normalizeToolCall.js";
import { normalizeToolResult } from "./events/normalizeToolResult.js";
import { normalizeMessage } from "./events/normalizeMessage.js";
import { createLogger } from "./logger.js";
import { mapAuditDecision } from "./policy/decisionMapper.js";
import { TRACESHIELD_BLOCK_PREFIX } from "./policy/decisionMapper.js";
import { evaluateFallbackPolicy } from "./policy/fallbackPolicy.js";
import { DiskQueue } from "./queue/diskQueue.js";
import { MemoryQueue } from "./queue/memoryQueue.js";
import type { TraceEvent, TraceEventType } from "./types/event.js";
import type {
  OpenClawToolDecisionResult,
  RawMessageHookInput,
  RawToolCallHookInput,
  RawToolResultHookInput,
} from "./types/hook.js";
import { createId } from "./utils/id.js";
import { FlushWorker } from "./worker/flushWorker.js";

const queue = new MemoryQueue<TraceEvent>();
let flushWorker: FlushWorker | undefined;

const pluginEntry: unknown = definePluginEntry({
  id: "traceshield-security-plugin",
  name: "TraceShield Security Plugin",
  description: "Runtime security gate for OpenClaw tool calls and trace events.",
  register(api) {
    const config = loadConfig(api.pluginConfig ?? {});
    const logger = createLogger("traceshield-openclaw");
    const auditClient = new AuditClient({
      baseUrl: config.core_base_url,
      timeoutMs: config.audit_timeout_ms,
    });

    api.registerTool({
      name: "traceshield_status",
      label: "TraceShield status",
      description: "Show TraceShield plugin status, Core URL, fallback mode, and local event queue size.",
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {},
      },
      execute: async () => ({
        content: [
          {
            type: "text",
            text: [
              "TraceShield Security Plugin is loaded.",
              `Core URL: ${config.core_base_url}`,
              `Audit timeout: ${config.audit_timeout_ms}ms`,
              `Fallback enabled: ${String(config.fallback_enabled)}`,
              `Debug full payload: ${String(config.debug_full_payload)}`,
              `Queued events: ${String(queue.size())}`,
            ].join("\n"),
          },
        ],
      }),
    } as never);

    api.registerService({
      id: "traceshield-event-flush-worker",
      start(ctx) {
        const serviceLogger = createLogger("traceshield-flush-worker");
        flushWorker = new FlushWorker({
          memoryQueue: queue,
          diskQueue: new DiskQueue(config.disk_queue_dir),
          eventClient: new EventClient({
            baseUrl: config.core_base_url,
            timeoutMs: config.event_flush_timeout_ms,
          }),
          logger: serviceLogger,
          intervalMs: config.event_flush_interval_ms,
        });
        flushWorker.start();
        ctx.logger.info(`TraceShield flush worker started core=${config.core_base_url}`);
      },
      stop(ctx) {
        flushWorker?.stop();
        ctx.logger.info("TraceShield flush worker stopped");
      },
    });

    on(api, "before_prompt_build", () => ({
      appendSystemContext: [
        "TraceShield security plugin guidance:",
        `If a tool result starts with "${TRACESHIELD_BLOCK_PREFIX}", the requested operation was blocked and not executed.`,
        "In that case, tell the user clearly that TraceShield blocked the tool call. Do not say the task is complete.",
      ].join("\n"),
    }), { priority: 60, timeoutMs: 1_000 });

    api.registerAgentToolResultMiddleware?.((event: {
      result?: {
        content?: Array<{ type?: string; text?: string }>;
        details?: unknown;
      };
    }) => {
      const text = event.result?.content
        ?.map((entry) => entry.type === "text" ? entry.text ?? "" : "")
        .join("\n") ?? "";

      if (!text.startsWith(TRACESHIELD_BLOCK_PREFIX)) {
        return undefined;
      }

      return {
        result: {
          ...event.result,
          content: [
            {
              type: "text",
              text: [
                text,
                "",
                "Visible outcome: TraceShield blocked this tool call before execution.",
              ].join("\n"),
            },
          ],
          details: {
            status: "blocked",
            source: "traceshield-security-plugin",
            reason: text,
          },
        },
      };
    }, { runtimes: ["openclaw"] });

    for (const hookName of [
      "message_received",
      "llm_input",
      "llm_output",
      "message_sending",
      "agent_end",
    ] as const) {
      on(api, hookName, (event: unknown, ctx: Record<string, unknown>) => {
        queue.enqueue(
          normalizeMessage(
            hookName as Extract<
              TraceEventType,
              "message_received" | "llm_input" | "llm_output" | "message_sending" | "agent_end"
            >,
            toRawMessageInput(event, ctx),
            config,
          ),
        );
      }, { priority: 80, timeoutMs: 2_000 });
    }

    on(api, "before_tool_call", async (event: unknown, ctx: Record<string, unknown>) => {
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
    }, { priority: 100, timeoutMs: config.audit_timeout_ms + 200 });

    on(api, "after_tool_call", (event: unknown, ctx: Record<string, unknown>) => {
      queue.enqueue(normalizeToolResult(toRawToolResultInput(event, ctx), config));
    }, { priority: 80, timeoutMs: 2_000 });

    api.registerSecurityAuditCollector(() => [
      {
        checkId: "traceshield-openclaw-plugin-enabled",
        title: "TraceShield plugin is enabled",
        severity: "info",
        detail: `TraceShield audits before_tool_call via ${config.core_base_url}`,
      },
    ]);

    api.logger.info(
      `TraceShield Security Plugin registered core=${config.core_base_url} auditTimeoutMs=${config.audit_timeout_ms} fallback=${config.fallback_enabled}`,
    );
  },
});

export default pluginEntry;

function on(
  api: unknown,
  name: string,
  handler: (event: unknown, ctx: Record<string, unknown>) => unknown,
  opts?: Record<string, unknown>,
): void {
  const typedApi = api as {
    on?: (name: string, handler: (event: unknown, ctx: Record<string, unknown>) => unknown, opts?: Record<string, unknown>) => void;
    registerHook?: (name: string, handler: (event: unknown) => unknown, opts?: Record<string, unknown>) => void;
  };

  if (typedApi.on) {
    typedApi.on(name, handler, opts);
    return;
  }

  typedApi.registerHook?.(name, (event) => handler(event, {}), opts);
}

function toRawMessageInput(event: unknown, ctx: Record<string, unknown>): RawMessageHookInput {
  const input = asRecord(event);
  const context = asRecord(ctx);
  const raw: RawMessageHookInput = {
    content: input.content ?? input.body ?? input.prompt ?? input.output ?? input.message,
    metadata: { event: input, context },
  };
  assignOptionalString(raw, "session_id", readString(context.sessionId) ?? readString(context.sessionKey));
  assignOptionalString(raw, "run_id", readString(input.runId) ?? readString(context.runId));
  assignOptionalString(raw, "trace_id", readTraceId(context.trace) ?? readString(input.traceId));
  assignOptionalString(raw, "message_id", readString(input.messageId));
  assignOptionalString(raw, "role", readString(input.role));
  return raw;
}

function toRawToolCallInput(event: unknown, ctx: Record<string, unknown>): RawToolCallHookInput {
  const input = asRecord(event);
  const context = asRecord(ctx);
  const raw: RawToolCallHookInput = {
    tool_name: readString(input.toolName) ?? "unknown",
    params: asRecord(input.params),
    metadata: { derivedPaths: input.derivedPaths, context },
  };
  assignOptionalString(raw, "session_id", readString(context.sessionId) ?? readString(context.sessionKey));
  assignOptionalString(raw, "run_id", readString(input.runId) ?? readString(context.runId));
  assignOptionalString(raw, "trace_id", readTraceId(context.trace) ?? readString(input.traceId));
  assignOptionalString(raw, "workspace_root", readString(context.workspaceDir) ?? readString(context.cwd));
  assignOptionalString(raw, "tool_call_id", readString(input.toolCallId));
  assignOptionalString(raw, "tool_kind", readString(input.toolKind) ?? readString(context.toolKind));
  return raw;
}

function toRawToolResultInput(event: unknown, ctx: Record<string, unknown>): RawToolResultHookInput {
  const input = asRecord(event);
  const raw: RawToolResultHookInput = toRawToolCallInput(event, ctx);
  raw.result = input.result;
  raw.error = input.error;
  if (typeof input.durationMs === "number") {
    raw.duration_ms = input.durationMs;
  }
  return raw;
}

function toOpenClawBeforeToolResult(result: OpenClawToolDecisionResult): Record<string, unknown> | undefined {
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
    ? value as Record<string, unknown>
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
