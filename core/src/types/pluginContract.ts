export type AuditAction = "ALLOW" | "WARN" | "ASK" | "BLOCK";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface AuditRequestContext {
  user_goal?: string;
  recent_message_hashes?: string[];
  workspace_root?: string;
}

export interface AuditRequest {
  request_id: string;
  schema_version: "v1";
  session_id: string;
  run_id: string;
  trace_id: string;
  tool_call_id: string;
  tool_name: string;
  tool_kind: string;
  raw_params: Record<string, unknown>;
  param_summary: Record<string, unknown>;
  resource_hint?: string;
  risk_hint?: string;
  context: AuditRequestContext;
}

export interface AuditApproval {
  approval_id: string;
  title: string;
  description: string;
  default_action: "ALLOW" | "BLOCK";
  timeout_ms: number;
}

export interface AuditDecision {
  decision: AuditAction;
  risk_level: RiskLevel;
  reason: string;
  matched_rules: string[];
  policy_version?: string;
  evidence_refs?: string[];
  modified_params?: Record<string, unknown> | null;
  approval?: AuditApproval | null;
  fallback_used?: boolean;
}

export type TraceEventType =
  | "message_received"
  | "llm_input"
  | "llm_output"
  | "message_sending"
  | "before_tool_call"
  | "after_tool_call"
  | "agent_end"
  | "fallback_decision";

export interface TraceEvent {
  event_id: string;
  schema_version: "v1";
  type: TraceEventType;
  timestamp: number;
  plugin_id: string;
  gateway_id?: string;
  session_id: string;
  run_id: string;
  trace_id: string;
  mode: "sync" | "async";
  payload: Record<string, unknown>;
}
