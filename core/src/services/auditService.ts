import type { PoolClient } from "pg";
import { config } from "../config.js";
import { pool, withTransaction } from "../db/pool.js";
import type { DecisionRow } from "../types/db.js";
import type { AuditApproval, AuditDecision, AuditRequest } from "../types/pluginContract.js";
import { createDecisionEvidence } from "./evidenceService.js";
import { evaluatePolicy } from "./policyEngine.js";

export async function auditToolCall(request: AuditRequest): Promise<AuditDecision> {
  const existing = await pool.query<DecisionRow>(
    "SELECT * FROM audit_decisions WHERE request_id = $1",
    [request.request_id],
  );
  const existingRow = existing.rows[0];
  if (existingRow) {
    return mapDecisionRow(existingRow);
  }

  const policyDecision = evaluatePolicy(request);

  return withTransaction(async (client) => {
    await upsertSessionAndRun(client, request);
    await client.query(
      `INSERT INTO tool_calls (
         tool_call_id, request_id, session_id, run_id, trace_id, tool_name, tool_kind,
         param_summary, resource_hint, risk_hint, raw_params, status, started_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11::jsonb, 'pending', NOW(), NOW())
       ON CONFLICT (tool_call_id) DO UPDATE SET
         request_id = COALESCE(tool_calls.request_id, EXCLUDED.request_id),
         session_id = EXCLUDED.session_id,
         run_id = EXCLUDED.run_id,
         trace_id = EXCLUDED.trace_id,
         tool_name = EXCLUDED.tool_name,
         tool_kind = EXCLUDED.tool_kind,
         param_summary = EXCLUDED.param_summary,
         resource_hint = EXCLUDED.resource_hint,
         risk_hint = EXCLUDED.risk_hint,
         raw_params = EXCLUDED.raw_params,
         updated_at = NOW()`,
      [
        request.tool_call_id,
        request.request_id,
        request.session_id,
        request.run_id,
        request.trace_id,
        request.tool_name,
        request.tool_kind,
        JSON.stringify(request.param_summary),
        request.resource_hint ?? null,
        request.risk_hint ?? null,
        config.saveRawParams ? JSON.stringify(request.raw_params) : null,
      ],
    );

    const decisionResult = await client.query<{ decision_id: string }>(
      `INSERT INTO audit_decisions (
         request_id, tool_call_id, decision, risk_level, reason, matched_rules,
         policy_version, modified_params, approval, fallback_used
       ) VALUES ($1, $2, $3, $4, $5, $6::text[], 'v1', NULL, $7::jsonb, FALSE)
       RETURNING decision_id::text`,
      [
        request.request_id,
        request.tool_call_id,
        policyDecision.decision,
        policyDecision.riskLevel,
        policyDecision.reason,
        policyDecision.matchedRules,
        policyDecision.approval ? JSON.stringify(policyDecision.approval) : null,
      ],
    );
    const decisionId = decisionResult.rows[0]?.decision_id;
    if (!decisionId) {
      throw new Error("Failed to persist audit decision");
    }

    for (const policyId of policyDecision.matchedRules) {
      await client.query(
        `INSERT INTO audit_rule_hits (decision_id, policy_id, matched, detail)
         VALUES ($1, $2, TRUE, $3::jsonb)
         ON CONFLICT (decision_id, policy_id) DO NOTHING`,
        [
          decisionId,
          policyId,
          JSON.stringify({
            tool_kind: request.tool_kind,
            resource_hint: request.resource_hint ?? null,
          }),
        ],
      );
    }

    const evidenceId = await createDecisionEvidence(client, request, decisionId, policyDecision);
    await client.query(
      "UPDATE audit_decisions SET evidence_refs = ARRAY[$1]::text[] WHERE decision_id = $2",
      [evidenceId, decisionId],
    );
    await refreshRunAggregates(client, request.run_id);

    return {
      decision: policyDecision.decision,
      risk_level: policyDecision.riskLevel,
      reason: policyDecision.reason,
      matched_rules: policyDecision.matchedRules,
      policy_version: "v1",
      evidence_refs: [evidenceId],
      modified_params: null,
      approval: policyDecision.approval,
      fallback_used: false,
    };
  });
}

async function upsertSessionAndRun(client: PoolClient, request: AuditRequest): Promise<void> {
  await client.query(
    `INSERT INTO audit_sessions (session_id, first_seen_at, last_seen_at)
     VALUES ($1, NOW(), NOW())
     ON CONFLICT (session_id) DO UPDATE SET last_seen_at = NOW()`,
    [request.session_id],
  );
  await client.query(
    `INSERT INTO audit_runs (run_id, session_id, trace_id, started_at, last_seen_at)
     VALUES ($1, $2, $3, NOW(), NOW())
     ON CONFLICT (run_id) DO UPDATE SET
       session_id = EXCLUDED.session_id,
       trace_id = EXCLUDED.trace_id,
       last_seen_at = NOW()`,
    [request.run_id, request.session_id, request.trace_id],
  );
}

async function refreshRunAggregates(client: PoolClient, runId: string): Promise<void> {
  await client.query(
    `WITH summary AS (
       SELECT
         COUNT(DISTINCT tc.tool_call_id)::int AS tool_call_count,
         COUNT(*) FILTER (WHERE ad.decision = 'BLOCK')::int AS blocked_count,
         COUNT(*) FILTER (WHERE ad.decision = 'WARN')::int AS warn_count,
         COUNT(*) FILTER (WHERE ad.decision = 'ASK')::int AS ask_count,
         COALESCE(MAX(CASE ad.risk_level
           WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END), 1) AS risk_rank,
         COALESCE(MAX(CASE ad.decision
           WHEN 'BLOCK' THEN 4 WHEN 'ASK' THEN 3 WHEN 'WARN' THEN 2 ELSE 1 END), 1) AS decision_rank
       FROM tool_calls tc
       LEFT JOIN audit_decisions ad ON ad.tool_call_id = tc.tool_call_id
       WHERE tc.run_id = $1
     )
     UPDATE audit_runs ar SET
       tool_call_count = summary.tool_call_count,
       blocked_count = summary.blocked_count,
       warn_count = summary.warn_count,
       ask_count = summary.ask_count,
       risk_level = CASE summary.risk_rank
         WHEN 4 THEN 'critical' WHEN 3 THEN 'high' WHEN 2 THEN 'medium' ELSE 'low' END,
       final_decision = CASE summary.decision_rank
         WHEN 4 THEN 'BLOCK' WHEN 3 THEN 'ASK' WHEN 2 THEN 'WARN' ELSE 'ALLOW' END,
       last_seen_at = NOW()
     FROM summary
     WHERE ar.run_id = $1`,
    [runId],
  );
}

function mapDecisionRow(row: DecisionRow): AuditDecision {
  return {
    decision: row.decision,
    risk_level: row.risk_level,
    reason: row.reason,
    matched_rules: row.matched_rules,
    policy_version: row.policy_version,
    evidence_refs: row.evidence_refs,
    modified_params: row.modified_params,
    approval: row.approval as AuditApproval | null,
    fallback_used: row.fallback_used,
  };
}
