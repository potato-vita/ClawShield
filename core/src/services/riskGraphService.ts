import { pool } from "../db/pool.js";

interface ToolNodeRow {
  tool_call_id: string;
  tool_name: string;
  tool_kind: string;
  resource_hint: string | null;
  status: string;
  started_at: Date;
  decision: string | null;
  risk_level: string | null;
  reason: string | null;
  matched_rules: string[] | null;
}

interface EvidenceStepRow {
  tool_call_id: string | null;
  evidence_step_id: string;
  step_order: number;
  step_type: string;
  title: string;
  detail: Record<string, unknown>;
}

export class RunNotFoundError extends Error {}

export async function buildRiskGraph(runId: string): Promise<{
  run_id: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}> {
  const runResult = await pool.query<{ run_id: string }>(
    "SELECT run_id FROM audit_runs WHERE run_id = $1",
    [runId],
  );
  if (runResult.rowCount === 0) {
    throw new RunNotFoundError(`Run ${runId} was not found`);
  }

  const [toolsResult, evidenceResult] = await Promise.all([
    pool.query<ToolNodeRow>(
      `SELECT
         tc.tool_call_id, tc.tool_name, tc.tool_kind, tc.resource_hint, tc.status, tc.started_at,
         latest.decision, latest.risk_level, latest.reason, latest.matched_rules
       FROM tool_calls tc
       LEFT JOIN LATERAL (
         SELECT ad.decision, ad.risk_level, ad.reason, ad.matched_rules
         FROM audit_decisions ad
         WHERE ad.tool_call_id = tc.tool_call_id
         ORDER BY ad.created_at DESC
         LIMIT 1
       ) latest ON TRUE
       WHERE tc.run_id = $1
       ORDER BY tc.started_at ASC, tc.tool_call_id ASC`,
      [runId],
    ),
    pool.query<EvidenceStepRow>(
      `SELECT evidence_step_id::text, tool_call_id, step_order, step_type, title, detail
       FROM evidence_steps
       WHERE run_id = $1
       ORDER BY created_at ASC, step_order ASC`,
      [runId],
    ),
  ]);

  const evidenceByTool = new Map<string, EvidenceStepRow[]>();
  for (const step of evidenceResult.rows) {
    if (!step.tool_call_id) {
      continue;
    }
    const current = evidenceByTool.get(step.tool_call_id) ?? [];
    current.push(step);
    evidenceByTool.set(step.tool_call_id, current);
  }

  const nodes: Array<Record<string, unknown>> = [
    {
      id: `user:${runId}`,
      type: "user_request",
      label: "User Request",
      risk_level: "low",
    },
  ];
  const edges: Array<Record<string, unknown>> = [];
  let previousNodeId = `user:${runId}`;

  for (const tool of toolsResult.rows) {
    const nodeId = `tool:${tool.tool_call_id}`;
    nodes.push({
      id: nodeId,
      type: "tool_call",
      label: tool.tool_name,
      tool_call_id: tool.tool_call_id,
      tool_kind: tool.tool_kind,
      resource_hint: tool.resource_hint,
      status: tool.status,
      decision: tool.decision,
      risk_level: tool.risk_level ?? "low",
      reason: tool.reason,
      matched_rules: tool.matched_rules ?? [],
      started_at: tool.started_at,
      evidence_steps: evidenceByTool.get(tool.tool_call_id) ?? [],
    });
    edges.push({
      id: `flow:${previousNodeId}:${nodeId}`,
      source: previousNodeId,
      target: nodeId,
      type: "flow",
    });
    previousNodeId = nodeId;
  }

  return { run_id: runId, nodes, edges };
}
