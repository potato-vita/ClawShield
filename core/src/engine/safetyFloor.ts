import type { AuditRequest } from "../types/pluginContract.js";
import type { PolicyDecision } from "../services/policyEngine.js";

const secretPattern = /(\.env(?:\b|[./])|id_rsa\b|id_ed25519\b|private[_\s-]?key|\/etc\/shadow\b)/i;
const destructiveDiskPattern = /(\brm\s+(?:-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\b|\bmkfs(?:\.[a-z0-9]+)?\b|\bdd\s+[^\n]*\bif\s*=)/i;

export function evaluateSafetyFloor(request: AuditRequest): PolicyDecision | null {
  const text = JSON.stringify({ params: request.raw_params, resource: request.resource_hint });
  if (["file_read", "shell_exec"].includes(request.tool_kind) && secretPattern.test(text)) {
    return {
      decision: "BLOCK",
      riskLevel: "critical",
      reason: "Safety floor blocked explicit secret or private-key access.",
      matchedRules: ["safety_floor_secret_access"],
      approval: null,
    };
  }
  if (request.tool_kind === "shell_exec" && destructiveDiskPattern.test(text)) {
    return {
      decision: "ASK",
      riskLevel: "critical",
      reason: "Safety floor requires approval for an explicit destructive disk command.",
      matchedRules: ["safety_floor_destructive_disk"],
      approval: {
        approval_id: `safety_${request.request_id}`,
        title: "Confirm destructive disk command",
        description: "This command can remove or overwrite local data.",
        default_action: "BLOCK",
        timeout_ms: 30_000,
      },
    };
  }
  return null;
}

