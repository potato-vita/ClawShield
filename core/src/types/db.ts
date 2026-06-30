import type { AuditAction, RiskLevel } from "./pluginContract.js";

export interface RuntimeStatus {
  tool_calls_24h: number;
  blocked_24h: number;
  high_risk_24h: number;
  policy_hits_24h: number;
}

export interface DecisionRow {
  decision_id: string;
  request_id: string;
  tool_call_id: string;
  decision: AuditAction;
  risk_level: RiskLevel;
  reason: string;
  matched_rules: string[];
  policy_version: string;
  evidence_refs: string[];
  modified_params: Record<string, unknown> | null;
  approval: Record<string, unknown> | null;
  fallback_used: boolean;
  created_at: Date;
}
