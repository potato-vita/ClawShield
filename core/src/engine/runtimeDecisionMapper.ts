import { randomUUID } from "node:crypto";
import type { MethodEvaluationResult } from "../types/methodContract.js";
import type { PolicyDecision } from "../services/policyEngine.js";

export function mapRuntimeDecision(result: MethodEvaluationResult): PolicyDecision {
  const reason = currentReason(result);
  return {
    decision: result.runtime_suggestion,
    riskLevel: result.risk_level,
    reason,
    matchedRules: result.current_step_violations.map((item) => String(item.violation_type ?? "method_violation")),
    approval:
      result.runtime_suggestion === "ASK"
        ? {
            approval_id: `method_${randomUUID()}`,
            title: "TraceShield method approval",
            description: reason,
            default_action: "BLOCK",
            timeout_ms: 30_000,
          }
        : null,
  };
}

function currentReason(result: MethodEvaluationResult): string {
  const first = result.current_step_violations[0];
  if (first?.reason) return String(first.reason);
  if (result.runtime_suggestion === "WARN") return "TraceShield detected historical or low-confidence runtime risk.";
  if (result.runtime_suggestion === "ASK") return "TraceShield requires approval for this runtime action.";
  if (result.runtime_suggestion === "BLOCK") return "TraceShield method engine blocked this runtime action.";
  return "TraceShield method engine found no current-step violation.";
}

