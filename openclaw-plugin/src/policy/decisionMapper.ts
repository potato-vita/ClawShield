import type { AuditDecision } from "../types/decision.js";
import type { OpenClawToolDecisionResult } from "../types/hook.js";

export const TRACESHIELD_BLOCK_PREFIX = "TraceShield BLOCKED";

export function mapAuditDecision(decision: AuditDecision): OpenClawToolDecisionResult {
  const base = { auditDecision: decision };

  if (decision.modified_params) {
    return {
      ...base,
      modifiedParams: decision.modified_params,
      ...(decision.decision === "WARN" ? { warning: decision.reason } : {}),
    };
  }

  switch (decision.decision) {
    case "ALLOW":
      return base;
    case "WARN":
      return {
        ...base,
        warning: decision.reason,
      };
    case "ASK":
      if (!decision.approval) {
        return {
          ...base,
          block: true,
          blockReason: formatTraceShieldBlockReason(
            "TraceShield requires approval, but approval payload is missing.",
            decision,
          ),
        };
      }

      return {
        ...base,
        requireApproval: {
          approvalId: decision.approval.approval_id,
          title: decision.approval.title,
          description: decision.approval.description,
          defaultAction: decision.approval.default_action,
          timeoutMs: decision.approval.timeout_ms,
        },
      };
    case "BLOCK":
      return {
        ...base,
        block: true,
        blockReason: formatTraceShieldBlockReason(decision.reason, decision),
      };
  }
}

export function formatTraceShieldBlockReason(reason: string, decision?: AuditDecision): string {
  const lines = [
    `${TRACESHIELD_BLOCK_PREFIX}: tool call was blocked and was not executed.`,
    `Reason: ${reason}`,
  ];

  if (decision?.risk_level) {
    lines.push(`Risk level: ${decision.risk_level}`);
  }

  if (decision?.matched_rules?.length) {
    lines.push(`Matched rules: ${decision.matched_rules.join(", ")}`);
  }

  lines.push("User-visible status: TraceShield stopped this operation. Do not summarize it as completed.");
  return lines.join("\n");
}
