import type { PoolClient } from "pg";
import { pool } from "../db/pool.js";

export interface ObservationDetection {
  injection_detected: boolean;
  injection_score: number;
  injection_reasons: string[];
  observation_hash: string | null;
}

const pending = new Map<string, ObservationDetection>();

export async function recordObservationDetection(
  toolCallId: string,
  detection: ObservationDetection,
): Promise<void> {
  const result = await pool.query(
    `UPDATE tool_results SET injection_detected=$2, injection_score=$3,
       injection_reasons=$4::jsonb, observation_hash=$5, trace_completeness='complete'
     WHERE tool_call_id=$1`,
    [
      toolCallId,
      detection.injection_detected,
      detection.injection_score,
      JSON.stringify(detection.injection_reasons),
      detection.observation_hash,
    ],
  );
  if (result.rowCount === 0) pending.set(toolCallId, detection);
}

export async function applyPendingObservationDetection(
  client: PoolClient,
  toolCallId: string,
): Promise<void> {
  const detection = pending.get(toolCallId);
  if (!detection) return;
  await client.query(
    `UPDATE tool_results SET injection_detected=$2, injection_score=$3,
       injection_reasons=$4::jsonb, observation_hash=$5, trace_completeness='complete'
     WHERE tool_call_id=$1`,
    [
      toolCallId,
      detection.injection_detected,
      detection.injection_score,
      JSON.stringify(detection.injection_reasons),
      detection.observation_hash,
    ],
  );
  pending.delete(toolCallId);
}

