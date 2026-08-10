import type { Decision, RiskLevel } from "./session";

export type GraphNodeType = "user_intent" | "tool_call" | "sensitive_object" | "network_sink" | "policy_decision" | "blocked";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  detail: string;
  risk: RiskLevel;
  stepSeq?: number;
  decision?: Decision;
  toolCallId?: string;
  evidenceStepId?: string;
  policyId?: string;
  lane?: "main" | "evidence";
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  kind?: "main" | "evidence";
}
