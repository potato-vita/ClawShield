import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type { RawToolResultHookInput } from "../types/hook.js";
import { createId } from "../utils/id.js";
import { normalizeContext } from "./context.js";
import { shortHash } from "../sanitizer/hash.js";
import { previewText, summarizeValue } from "../sanitizer/preview.js";
import { redactObject, redactText } from "../sanitizer/redact.js";
import { inferRiskHint, inferToolKind, summarizeParams } from "./normalizeToolCall.js";

export function normalizeToolResult(
  input: RawToolResultHookInput,
  config: PluginConfig,
): TraceEvent {
  const context = normalizeContext(input);
  const toolName = input.tool_name ?? "unknown";
  const toolKind = input.tool_kind ?? inferToolKind(toolName);
  const params = input.params ?? {};
  const resultPreview = config.debug_full_payload
    ? input.result
    : redactText(previewText(input.result));

  return {
    event_id: createId("evt"),
    schema_version: "v1",
    type: "after_tool_call",
    timestamp: Date.now(),
    plugin_id: config.plugin_id,
    ...(config.gateway_id ? { gateway_id: config.gateway_id } : {}),
    session_id: context.session_id,
    run_id: context.run_id,
    trace_id: context.trace_id,
    mode: "async",
    payload: {
      tool_call_id: input.tool_call_id,
      tool_name: toolName,
      tool_kind: toolKind,
      param_summary: summarizeParams(params),
      result_preview: resultPreview,
      result_hash: shortHash(input.result ?? ""),
      result_summary: summarizeValue(input.result),
      error: redactObject(input.error ?? null),
      duration_ms: input.duration_ms,
      risk_hint: inferRiskHint(toolKind, params),
    },
  };
}
