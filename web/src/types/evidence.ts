export interface EvidenceStep {
  id: string;
  step: string;
  type: "intent" | "tool" | "object" | "network" | "decision";
  title: string;
  detail: string;
  status: "observed" | "verified" | "risk" | "critical" | "blocked";
  nodeId: string;
  fingerprint?: string;
}
