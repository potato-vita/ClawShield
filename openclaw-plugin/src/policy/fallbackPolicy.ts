import type { AuditDecision } from "../types/decision.js";
import type { PluginConfig } from "../types/config.js";
import type { AuditRequest } from "../types/event.js";
import { defaultLocalPolicyCache, type LocalPolicyCache } from "./localPolicyCache.js";

export function evaluateFallbackPolicy(
  request: AuditRequest,
  config: PluginConfig,
  cache: LocalPolicyCache = defaultLocalPolicyCache,
): AuditDecision {
  if (isSensitiveRead(request)) {
    return block("critical", "Core unavailable; sensitive file read is blocked locally.", [
      "fallback_sensitive_read_block",
    ]);
  }

  if (config.high_risk_tool_kinds.includes(request.tool_kind)) {
    return block("critical", "Core unavailable; high-risk tool call is blocked locally.", [
      "fallback_high_risk_fail_closed",
    ]);
  }

  if (config.local_allow_tool_kinds.includes(request.tool_kind) && cache.hasAllow(request)) {
    return {
      decision: "ALLOW",
      risk_level: "low",
      reason: "Core unavailable; local allow cache matched.",
      matched_rules: ["fallback_local_allow_cache"],
      fallback_used: true,
    };
  }

  return {
    decision: "ASK",
    risk_level: "medium",
    reason: "Core unavailable; unknown or uncached tool call requires approval.",
    matched_rules: ["fallback_unknown_requires_approval"],
    approval: {
      approval_id: `fallback_${Date.now()}`,
      title: "TraceShield fallback approval",
      description: "Core is unavailable. Confirm whether this tool call should continue.",
      default_action: "BLOCK",
      timeout_ms: 30000,
    },
    fallback_used: true,
  };
}

function block(
  riskLevel: AuditDecision["risk_level"],
  reason: string,
  matchedRules: string[],
): AuditDecision {
  return {
    decision: "BLOCK",
    risk_level: riskLevel,
    reason,
    matched_rules: matchedRules,
    fallback_used: true,
  };
}

function isSensitiveRead(request: AuditRequest): boolean {
  // 覆盖 file_read 和通过 shell 读取敏感文件的场景
  if (request.tool_kind !== "file_read" && request.tool_kind !== "shell_exec") {
    return false;
  }

  const target =
    `${request.resource_hint ?? ""} ${JSON.stringify(request.raw_params)}`.toLowerCase();
  return (
    target.includes(".env") ||
    target.includes("id_rsa") ||
    target.includes("id_dsa") ||
    target.includes("id_ed25519") ||
    target.includes("private_key") ||
    target.includes("/etc/shadow") ||
    target.includes("/etc/passwd") ||
    /\bcat\b.*\b(\.env|\.pem|private|secret|token)\b/i.test(target) ||
    /\bcurl\b.*\b(\.env|\.pem|private|secret|token)\b/i.test(target)
  );
}
