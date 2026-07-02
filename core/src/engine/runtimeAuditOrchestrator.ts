import { config } from "../config.js";
import type { PolicyDecision } from "../services/policyEngine.js";
import { evaluateLegacyPolicy } from "../services/legacyPolicyEngine.js";
import { methodShadowService } from "../services/methodShadowService.js";
import type { AuditRequest } from "../types/pluginContract.js";
import type { MethodEvaluationResult } from "../types/methodContract.js";
import { combineWithSafetyFloor } from "./decisionCombiner.js";
import { mapRuntimeDecision } from "./runtimeDecisionMapper.js";
import { evaluateSafetyFloor } from "./safetyFloor.js";

export interface RuntimeAuditOutcome {
  decision: PolicyDecision;
  legacyDecision: PolicyDecision;
  engine: "method" | "legacy";
  engineVersion: string;
  methodResult?: MethodEvaluationResult;
}

export async function orchestrateRuntimeAudit(request: AuditRequest): Promise<RuntimeAuditOutcome> {
  const legacyDecision = evaluateLegacyPolicy(request);
  if (config.engineMode !== "enforce") {
    return { decision: legacyDecision, legacyDecision, engine: "legacy", engineVersion: "v1" };
  }
  try {
    const methodResult = await methodShadowService.evaluateForEnforcement(request);
    const decision = combineWithSafetyFloor(mapRuntimeDecision(methodResult), evaluateSafetyFloor(request));
    return {
      decision,
      legacyDecision,
      engine: "method",
      engineVersion: config.methodVersion,
      methodResult,
    };
  } catch {
    return { decision: legacyDecision, legacyDecision, engine: "legacy", engineVersion: "v1" };
  }
}

