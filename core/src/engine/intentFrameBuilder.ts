import type { AuditRequest } from "../types/pluginContract.js";
import type { RuntimeIntentFrame } from "../types/methodContract.js";

export interface BuiltIntentFrame {
  frame: RuntimeIntentFrame;
  version: "intent-v1";
  source: "audit_context" | "message_summary" | "empty";
  confidence: "high" | "medium" | "low";
}

export function buildIntentFrame(request: AuditRequest, recentUserSummary?: string): BuiltIntentFrame {
  const goal = request.context.user_goal?.trim() || recentUserSummary?.trim() || "";
  const source = request.context.user_goal
    ? "audit_context"
    : recentUserSummary
      ? "message_summary"
      : "empty";
  const workspace = request.context.workspace_root;
  return {
    frame: {
      task_goal: goal,
      allowed_actions: ["list_files", "read_file", "summarize_text", "status_read", "final_answer"],
      allowed_resources: workspace ? [workspace, `${workspace}/**`] : [],
      forbidden_actions: [],
      forbidden_resources: [".env", "id_rsa", "id_ed25519", "/etc/shadow"],
      sensitive_resources: [".env", "id_rsa", "id_ed25519", "private_key", "token", "secret"],
      constraints: { workspace_root: workspace ?? null },
      authorized_risky_calls: [],
    },
    version: "intent-v1",
    source,
    confidence: source === "audit_context" ? "high" : source === "message_summary" ? "medium" : "low",
  };
}
