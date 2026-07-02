import type { RiskLevel } from "./session";

export interface Policy {
  id: string;
  name: string;
  ruleId: string;
  severity: RiskLevel;
  action: "BLOCK" | "REVIEW" | "ALERT";
  enabled: boolean;
  hitCount: number;
  lastHitTime: string;
  description: string;
}
