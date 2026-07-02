import type { AuditAction, RiskLevel } from "./pluginContract.js";

export interface RuntimeIntentFrame {
  task_goal: string;
  allowed_actions: string[];
  allowed_resources: string[];
  forbidden_actions: string[];
  forbidden_resources: string[];
  sensitive_resources: string[];
  constraints: Record<string, unknown>;
  authorized_risky_calls: Array<Record<string, unknown>>;
}

export interface RuntimeTraceEvent {
  step_id: number;
  tool_name: string;
  tool_kind: string;
  semantic_action_hint?: string;
  target_resource_hint?: string;
  args: Record<string, unknown>;
  observation?: string | null;
  observation_hash?: string | null;
  status: "pending" | "completed" | "error" | "unknown";
}

export interface MethodEvaluationResult {
  method_decision: string;
  runtime_suggestion: AuditAction;
  risk_level: RiskLevel;
  current_step_violations: Array<Record<string, unknown>>;
  all_violations: Array<Record<string, unknown>>;
  semantic_events: Array<Record<string, unknown>>;
  risk_paths: number[][];
  graph_projection: { nodes: unknown[]; edges: unknown[] };
  mapping: Record<string, unknown>;
  latency_ms?: number;
}

