import type { Decision, RiskLevel } from "./session";

export interface ToolCall {
  id: string;
  sessionId: string;
  runId: string;
  time: string;
  toolName: string;
  toolKind: "shell" | "filesystem" | "transform" | "network";
  resource: string;
  decision: Decision;
  riskLevel: RiskLevel;
  latencyMs: number;
  policyHits: string[];
  argumentsSummary: string;
  nodeId: string;
}
