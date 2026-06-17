import { normalizeMessage } from "../events/normalizeMessage.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent, TraceEventType } from "../types/event.js";
import type { RawMessageHookInput } from "../types/hook.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";

const MESSAGE_EVENT_TYPES: Array<
  Extract<
    TraceEventType,
    "message_received" | "llm_input" | "llm_output" | "message_sending" | "agent_end"
  >
> = ["message_received", "llm_input", "llm_output", "message_sending", "agent_end"];

export interface RegisterMessageHooksOptions {
  api: unknown;
  queue: MemoryQueue<TraceEvent>;
  config: PluginConfig;
  on: (
    api: unknown,
    name: string,
    handler: (event: unknown, ctx: Record<string, unknown>) => unknown,
    opts?: Record<string, unknown>,
  ) => void;
}

/**
 * 注册消息类 Hook：采集消息、模型输入输出和 agent 结束事件。
 * 所有事件进入内存队列，不做阻断。
 */
export function registerMessageHooks(options: RegisterMessageHooksOptions): void {
  const { api, queue, config, on } = options;

  for (const hookName of MESSAGE_EVENT_TYPES) {
    on(
      api,
      hookName,
      (event: unknown, ctx: Record<string, unknown>) => {
        queue.enqueue(normalizeMessage(hookName, toRawMessageInput(event, ctx), config));
      },
      { priority: 80, timeoutMs: 2_000 },
    );
  }
}

function toRawMessageInput(event: unknown, ctx: Record<string, unknown>): RawMessageHookInput {
  const input = asRecord(event);
  const context = asRecord(ctx);
  const raw: RawMessageHookInput = {
    content: input.content ?? input.body ?? input.prompt ?? input.output ?? input.message,
    metadata: { event: input, context },
  };
  assignOptionalString(
    raw,
    "session_id",
    readString(context.sessionId) ?? readString(context.sessionKey),
  );
  assignOptionalString(raw, "run_id", readString(input.runId) ?? readString(context.runId));
  assignOptionalString(raw, "trace_id", readTraceId(context.trace) ?? readString(input.traceId));
  assignOptionalString(raw, "message_id", readString(input.messageId));
  assignOptionalString(raw, "role", readString(input.role));
  return raw;
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
