import type { PluginConfig } from "../types/config.js";
import type { TraceEvent, TraceEventType } from "../types/event.js";
import type { RawMessageHookInput } from "../types/hook.js";
import { createId } from "../utils/id.js";
import { normalizeContext } from "./context.js";
import { shortHash } from "../sanitizer/hash.js";
import { previewText, summarizeValue } from "../sanitizer/preview.js";
import { redactObject, redactText } from "../sanitizer/redact.js";

export function normalizeMessage(
  type: Extract<
    TraceEventType,
    "message_received" | "llm_input" | "llm_output" | "message_sending" | "agent_end"
  >,
  input: RawMessageHookInput,
  config: PluginConfig,
): TraceEvent {
  const context = normalizeContext(input);
  const content = config.debug_full_payload ? input.content : redactText(previewText(input.content));

  return {
    event_id: createId("evt"),
    schema_version: "v1",
    type,
    timestamp: Date.now(),
    plugin_id: config.plugin_id,
    ...(config.gateway_id ? { gateway_id: config.gateway_id } : {}),
    session_id: context.session_id,
    run_id: context.run_id,
    trace_id: context.trace_id,
    mode: "async",
    payload: {
      message_id: input.message_id,
      role: input.role,
      content,
      content_hash: shortHash(input.content ?? ""),
      summary: summarizeValue(input.content),
      metadata: redactObject(input.metadata ?? {}),
    },
  };
}
