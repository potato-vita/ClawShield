import { createHash } from "node:crypto";
import { pool, withTransaction } from "../db/pool.js";
import type { MethodEvaluationResult } from "../types/methodContract.js";

export interface MethodEvaluationSeed {
  requestId: string;
  toolCallId: string;
  runId: string;
  stepSeq?: number;
  profile: string;
  profileVersion: string;
  methodVersion: string;
  traceCompleteness: string;
  input: unknown;
  revision?: number;
}

export async function createMethodEvaluation(seed: MethodEvaluationSeed): Promise<string> {
  const result = await pool.query<{ method_evaluation_id: string }>(
    `INSERT INTO method_evaluations (
       request_id, tool_call_id, run_id, step_seq, profile, profile_version, method_version,
       status, trace_completeness, input_hash, evaluation_revision
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,'queued',$8,$9,$10)
     ON CONFLICT (request_id, profile, method_version, evaluation_revision)
     DO UPDATE SET status = method_evaluations.status
     RETURNING method_evaluation_id::text`,
    [
      seed.requestId,
      seed.toolCallId,
      seed.runId,
      seed.stepSeq ?? null,
      seed.profile,
      seed.profileVersion,
      seed.methodVersion,
      seed.traceCompleteness,
      createHash("sha256").update(JSON.stringify(seed.input)).digest("hex"),
      seed.revision ?? 1,
    ],
  );
  const id = result.rows[0]?.method_evaluation_id;
  if (!id) throw new Error("Failed to create method evaluation");
  return id;
}

export async function nextMethodEvaluationRevision(requestId: string): Promise<number> {
  const result = await pool.query<{ revision: number }>(
    "SELECT COALESCE(MAX(evaluation_revision), 0)::int + 1 AS revision FROM method_evaluations WHERE request_id=$1",
    [requestId],
  );
  return result.rows[0]?.revision ?? 1;
}

export async function markMethodRunning(id: string): Promise<void> {
  await pool.query("UPDATE method_evaluations SET status = 'running' WHERE method_evaluation_id = $1", [id]);
}

export async function completeMethodEvaluation(
  id: string,
  result: MethodEvaluationResult,
  diffType: string,
): Promise<void> {
  await withTransaction(async (client) => {
    await client.query(
      `UPDATE method_evaluations SET status='ok', method_decision=$2, runtime_suggestion=$3,
       risk_level=$4, latency_ms=$5, diff_type=$6, completed_at=NOW()
       WHERE method_evaluation_id=$1`,
      [id, result.method_decision, result.runtime_suggestion, result.risk_level, result.latency_ms ?? null, diffType],
    );
    for (const violation of result.all_violations) {
      const evidence = Array.isArray(violation.evidence_steps) ? violation.evidence_steps : [];
      await client.query(
        `INSERT INTO method_violations (
          method_evaluation_id, violation_type, source, reason, target, evidence_steps,
          is_current_step, metadata
        ) VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8::jsonb)`,
        [
          id,
          String(violation.violation_type ?? "unknown"),
          violation.source ? String(violation.source) : null,
          String(violation.reason ?? "Method violation"),
          violation.target ? String(violation.target) : null,
          JSON.stringify(evidence),
          result.current_step_violations.includes(violation),
          JSON.stringify(violation.metadata ?? {}),
        ],
      );
    }
    await client.query(
      `INSERT INTO method_graph_snapshots (method_evaluation_id, nodes, edges)
       VALUES ($1,$2::jsonb,$3::jsonb)
       ON CONFLICT (method_evaluation_id) DO UPDATE SET nodes=EXCLUDED.nodes, edges=EXCLUDED.edges`,
      [id, JSON.stringify(result.graph_projection.nodes), JSON.stringify(result.graph_projection.edges)],
    );
  });
}

export async function failMethodEvaluation(
  id: string,
  status: "timeout" | "error" | "unavailable",
  code: string,
  message: string,
): Promise<void> {
  await pool.query(
    `UPDATE method_evaluations SET status=$2, error_code=$3, error_message=$4, completed_at=NOW()
     WHERE method_evaluation_id=$1`,
    [id, status, code, message.slice(0, 2_000)],
  );
}
