import type { AuditRequest } from "../types/event.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type { RawToolCallHookInput } from "../types/hook.js";
import { createId } from "../utils/id.js";
import { normalizeContext } from "./context.js";
import { redactObject } from "../sanitizer/redact.js";

const riskHints = [
  "file_read",
  "file_write",
  "file_delete",
  "shell_exec",
  "network_request",
  "message_send",
  "plugin_install",
  "state_change",
  "unknown",
] as const;

export type RiskHint = (typeof riskHints)[number];

export function normalizeToolCall(
  input: RawToolCallHookInput,
  config: PluginConfig,
): TraceEvent {
  const context = normalizeContext(input);
  const toolName = input.tool_name ?? "unknown";
  const toolKind = input.tool_kind ?? inferToolKind(toolName);
  const params = input.params ?? {};

  return {
    event_id: createId("evt"),
    schema_version: "v1",
    type: "before_tool_call",
    timestamp: Date.now(),
    plugin_id: config.plugin_id,
    ...(config.gateway_id ? { gateway_id: config.gateway_id } : {}),
    session_id: context.session_id,
    run_id: context.run_id,
    trace_id: context.trace_id,
    mode: "async",
    payload: {
      tool_call_id: input.tool_call_id ?? createId("tool"),
      tool_name: toolName,
      tool_kind: toolKind,
      param_summary: summarizeParams(params),
      resource_hint: inferResourceHint(params),
      risk_hint: inferRiskHint(toolKind, params),
      metadata: redactObject(input.metadata ?? {}),
    },
  };
}

export function buildAuditRequest(
  input: RawToolCallHookInput,
): AuditRequest {
  const context = normalizeContext(input);
  const toolName = input.tool_name ?? "unknown";
  const toolKind = input.tool_kind ?? inferToolKind(toolName);
  const params = input.params ?? {};
  const resourceHint = inferResourceHint(params);

  return {
    request_id: createId("audit"),
    schema_version: "v1",
    session_id: context.session_id,
    run_id: context.run_id,
    trace_id: context.trace_id,
    tool_call_id: input.tool_call_id ?? createId("tool"),
    tool_name: toolName,
    tool_kind: toolKind,
    raw_params: params,
    param_summary: summarizeParams(params),
    ...(resourceHint ? { resource_hint: resourceHint } : {}),
    risk_hint: inferRiskHint(toolKind, params),
    context: {
      ...(context.user_goal ? { user_goal: context.user_goal } : {}),
      ...(context.recent_message_hashes
        ? { recent_message_hashes: context.recent_message_hashes }
        : {}),
      ...(context.workspace_root ? { workspace_root: context.workspace_root } : {}),
    },
  };
}

export function summarizeParams(params: Record<string, unknown>): Record<string, unknown> {
  const summary: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") {
      summary[key] = {
        type: "string",
        length: value.length,
        preview: value.slice(0, 120),
      };
      continue;
    }

    if (Array.isArray(value)) {
      summary[key] = { type: "array", length: value.length };
      continue;
    }

    if (value !== null && typeof value === "object") {
      summary[key] = {
        type: "object",
        keys: Object.keys(value as Record<string, unknown>).slice(0, 20),
      };
      continue;
    }

    summary[key] = value;
  }

  return redactObject(summary);
}

export function inferResourceHint(params: Record<string, unknown>): string | undefined {
  for (const key of ["path", "file", "filename", "url", "command", "cmd", "to"]) {
    const value = params[key];
    if (typeof value === "string" && value.length > 0) {
      return value.slice(0, 300);
    }
  }

  return undefined;
}

export function inferToolKind(toolName: string): string {
  const lower = toolName.toLowerCase();
  if (/(shell|bash|terminal|exec|command)/.test(lower)) {
    return "shell_exec";
  }
  if (/(write|patch|edit|save)/.test(lower)) {
    return "file_write";
  }
  if (/(delete|remove|unlink|rm)/.test(lower)) {
    return "file_delete";
  }
  if (/(http|fetch|request|curl|web)/.test(lower)) {
    return "network_request";
  }
  if (/(send|email|message|slack)/.test(lower)) {
    return "message_send";
  }
  if (/(install|plugin)/.test(lower)) {
    return "plugin_install";
  }
  if (/(read|open|cat)/.test(lower)) {
    return "file_read";
  }

  return "unknown";
}

export function inferRiskHint(
  toolKind: string,
  params: Record<string, unknown>,
): RiskHint {
  if (riskHints.includes(toolKind as RiskHint)) {
    return toolKind as RiskHint;
  }

  const text = JSON.stringify(params).toLowerCase();
  if (/\brm\s+-rf\b|delete|unlink/.test(text)) {
    return "file_delete";
  }
  if (/https?:\/\//.test(text)) {
    return "network_request";
  }
  if (/\b(npm|pip|brew|apt)\s+install\b/.test(text)) {
    return "plugin_install";
  }

  return "unknown";
}
