import type { AuditRequest } from "../types/pluginContract.js";
import type { RuntimeTraceEvent } from "../types/methodContract.js";

const actionByKind: Record<string, string> = {
  file_read: "read_file",
  file_write: "write_file",
  file_delete: "delete_file",
  shell_exec: "shell_exec",
  network_request: "network_post",
  message_send: "send_email",
  plugin_install: "install_plugin",
};

export function proposedEvent(request: AuditRequest): RuntimeTraceEvent {
  return {
    step_id: request.step_seq ?? 1,
    tool_name: request.tool_name,
    tool_kind: request.tool_kind,
    semantic_action_hint: actionByKind[request.tool_kind] ?? "unknown_tool_call",
    ...(request.resource_hint ? { target_resource_hint: request.resource_hint } : {}),
    args: request.raw_params,
    observation: null,
    observation_hash: null,
    status: "pending",
  };
}

