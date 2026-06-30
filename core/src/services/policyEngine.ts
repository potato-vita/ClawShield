import { randomUUID } from "node:crypto";
import type {
  AuditApproval,
  AuditRequest,
  AuditAction,
  RiskLevel,
} from "../types/pluginContract.js";

export interface PolicyDecision {
  decision: AuditAction;
  riskLevel: RiskLevel;
  reason: string;
  matchedRules: string[];
  approval: AuditApproval | null;
}

const secretPattern = /(\.env(?:\b|[./])|id_rsa\b|id_ed25519\b|private[_\s-]?key|\/etc\/shadow\b)/i;
const dangerousShellPattern = /(\brm\s+(?:-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\b|\bmkfs(?:\.[a-z0-9]+)?\b|\bdd\s+[^\n]*\bif\s*=)/i;

export function evaluatePolicy(request: AuditRequest): PolicyDecision {
  const haystack = JSON.stringify({
    tool_name: request.tool_name,
    tool_kind: request.tool_kind,
    raw_params: request.raw_params,
    param_summary: request.param_summary,
    resource_hint: request.resource_hint,
    risk_hint: request.risk_hint,
  });

  if (["file_read", "shell_exec"].includes(request.tool_kind) && secretPattern.test(haystack)) {
    return {
      decision: "BLOCK",
      riskLevel: "critical",
      reason: "Sensitive file or private-key access is blocked.",
      matchedRules: ["deny_secret_file_read"],
      approval: null,
    };
  }

  if (request.tool_kind === "shell_exec" && dangerousShellPattern.test(haystack)) {
    return {
      decision: "ASK",
      riskLevel: "critical",
      reason: "A destructive shell command requires explicit user approval.",
      matchedRules: ["confirm_dangerous_shell_command"],
      approval: {
        approval_id: `appr_${randomUUID()}`,
        title: "Confirm destructive shell command",
        description:
          "This command may recursively delete data or overwrite a filesystem. Continue only if you intended this exact operation.",
        default_action: "BLOCK",
        timeout_ms: 30_000,
      },
    };
  }

  if (request.tool_kind === "network_request" || request.risk_hint === "network_request") {
    const target = extractUrl(haystack);
    if (target && isExternalHost(target.hostname)) {
      return {
        decision: "ASK",
        riskLevel: "medium",
        reason: "External network access requires approval.",
        matchedRules: ["ask_external_network_request"],
        approval: {
          approval_id: `appr_${randomUUID()}`,
          title: "External network request",
          description: `Allow a request to ${target.hostname}?`,
          default_action: "BLOCK",
          timeout_ms: 30_000,
        },
      };
    }
  }

  if (request.tool_kind === "unknown" || request.tool_name === "unknown") {
    return {
      decision: "WARN",
      riskLevel: "medium",
      reason: "The tool is unknown and was allowed with a warning.",
      matchedRules: ["warn_unknown_tool"],
      approval: null,
    };
  }

  return {
    decision: "ALLOW",
    riskLevel: "low",
    reason: "No blocking policy matched this tool call.",
    matchedRules: ["default_allow"],
    approval: null,
  };
}

function extractUrl(value: string): URL | undefined {
  const match = value.match(/https?:\/\/[^\s"'{}\\]+/i);
  if (!match) {
    return undefined;
  }
  try {
    return new URL(match[0]);
  } catch {
    return undefined;
  }
}

function isExternalHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return !(
    normalized === "localhost" ||
    normalized === "::1" ||
    normalized === "127.0.0.1" ||
    normalized.startsWith("127.")
  );
}
