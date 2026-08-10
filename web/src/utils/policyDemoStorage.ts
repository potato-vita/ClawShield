import type { Policy } from "@/types/policy";

const STORAGE_KEY = "traceshield.policy-center.demo-state.v1";

export interface PolicyDemoState {
  version: 1;
  enabledByPolicyId: Record<string, boolean>;
  createdPolicies: Policy[];
}

export const emptyPolicyDemoState = (): PolicyDemoState => ({
  version: 1,
  enabledByPolicyId: {},
  createdPolicies: [],
});

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isPolicy = (value: unknown): value is Policy => {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.ruleId === "string" &&
    ["critical", "high", "medium", "low"].includes(String(value.severity)) &&
    ["BLOCK", "REVIEW", "ALERT"].includes(String(value.action)) &&
    typeof value.enabled === "boolean" &&
    typeof value.hitCount === "number" &&
    Number.isFinite(value.hitCount) &&
    typeof value.lastHitTime === "string" &&
    typeof value.description === "string"
  );
};

export function loadPolicyDemoState(): PolicyDemoState {
  if (typeof window === "undefined") return emptyPolicyDemoState();

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyPolicyDemoState();
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return emptyPolicyDemoState();

    const enabledByPolicyId: Record<string, boolean> = {};
    if (isRecord(parsed.enabledByPolicyId)) {
      for (const [policyId, enabled] of Object.entries(parsed.enabledByPolicyId)) {
        if (typeof enabled === "boolean") enabledByPolicyId[policyId] = enabled;
      }
    }

    const createdPolicies = Array.isArray(parsed.createdPolicies)
      ? parsed.createdPolicies.filter(isPolicy).map((policy) => ({ ...policy }))
      : [];

    return { version: 1, enabledByPolicyId, createdPolicies };
  } catch {
    return emptyPolicyDemoState();
  }
}

export function savePolicyDemoState(state: PolicyDemoState): boolean {
  if (typeof window === "undefined") return false;

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function mergePoliciesWithDemoState(
  policies: Policy[],
  state: PolicyDemoState,
): Policy[] {
  const seen = new Set<string>();
  const merged: Policy[] = [];

  const addPolicy = (source: Policy) => {
    if (seen.has(source.id)) return;
    seen.add(source.id);
    const override = state.enabledByPolicyId[source.id];
    merged.push({
      ...source,
      enabled: typeof override === "boolean" ? override : source.enabled,
    });
  };

  state.createdPolicies.forEach(addPolicy);
  policies.forEach(addPolicy);
  return merged;
}

export function rememberCreatedPolicy(
  state: PolicyDemoState,
  policy: Policy,
  previousId?: string,
): void {
  if (previousId && previousId !== policy.id) {
    state.createdPolicies = state.createdPolicies.filter(
      (item) => item.id !== previousId,
    );
    delete state.enabledByPolicyId[previousId];
  }

  const index = state.createdPolicies.findIndex((item) => item.id === policy.id);
  if (index === -1) state.createdPolicies.unshift({ ...policy });
  else state.createdPolicies[index] = { ...policy };
  state.enabledByPolicyId[policy.id] = policy.enabled;
}
