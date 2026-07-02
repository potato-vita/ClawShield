import type { PolicyDecision } from "../services/policyEngine.js";

const rank = { ALLOW: 1, WARN: 2, ASK: 3, BLOCK: 4 } as const;

export function combineWithSafetyFloor(
  method: PolicyDecision,
  floor: PolicyDecision | null,
): PolicyDecision {
  if (!floor || rank[method.decision] >= rank[floor.decision]) return method;
  return {
    ...floor,
    matchedRules: [...new Set([...method.matchedRules, ...floor.matchedRules])],
    reason: `${floor.reason} Method result: ${method.reason}`,
  };
}

