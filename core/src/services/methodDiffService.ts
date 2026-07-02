import type { AuditAction } from "../types/pluginContract.js";

export function classifyMethodDiff(legacy: AuditAction, method: AuditAction): string {
  if (legacy === method) return "same_action";
  if (legacy === "ALLOW" && method === "BLOCK") return "legacy_allow_method_block";
  if (legacy === "BLOCK" && method === "ALLOW") return "legacy_block_method_allow";
  if (legacy === "ASK" && method === "ALLOW") return "legacy_ask_method_allow";
  if (legacy === "ALLOW" && method === "WARN") return "legacy_allow_method_warn";
  return "risk_level_changed";
}

