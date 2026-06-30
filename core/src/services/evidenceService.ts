import type { PoolClient } from "pg";
import type { AuditRequest } from "../types/pluginContract.js";
import type { PolicyDecision } from "./policyEngine.js";

export async function createDecisionEvidence(
  client: PoolClient,
  request: AuditRequest,
  decisionId: string,
  policyDecision: PolicyDecision,
): Promise<string> {
  const evidenceResult = await client.query<{ evidence_id: string }>(
    `INSERT INTO evidence_items (
       run_id, tool_call_id, decision_id, evidence_type, summary, metadata
     ) VALUES ($1, $2, $3, 'policy_decision', $4, $5::jsonb)
     RETURNING evidence_id::text`,
    [
      request.run_id,
      request.tool_call_id,
      decisionId,
      policyDecision.reason,
      JSON.stringify({
        request_id: request.request_id,
        tool_name: request.tool_name,
        tool_kind: request.tool_kind,
        resource_hint: request.resource_hint ?? null,
      }),
    ],
  );
  const evidenceId = evidenceResult.rows[0]?.evidence_id;
  if (!evidenceId) {
    throw new Error("Failed to create evidence item");
  }

  const steps = [
    {
      order: 0,
      type: "tool_call",
      title: "Tool call received",
      detail: { tool_name: request.tool_name, tool_kind: request.tool_kind },
    },
    {
      order: 1,
      type: "policy_match",
      title: "Policy evaluation completed",
      detail: { matched_rules: policyDecision.matchedRules },
    },
    {
      order: 2,
      type: "decision",
      title: `${policyDecision.decision} decision issued`,
      detail: { risk_level: policyDecision.riskLevel, reason: policyDecision.reason },
    },
  ];

  for (const step of steps) {
    await client.query(
      `INSERT INTO evidence_steps (
         evidence_id, run_id, tool_call_id, step_order, step_type, title, detail
       ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)`,
      [
        evidenceId,
        request.run_id,
        request.tool_call_id,
        step.order,
        step.type,
        step.title,
        JSON.stringify(step.detail),
      ],
    );
  }

  return evidenceId;
}
