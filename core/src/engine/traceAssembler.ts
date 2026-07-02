import { pool } from "../db/pool.js";
import type { AuditRequest } from "../types/pluginContract.js";
import type { RuntimeTraceEvent } from "../types/methodContract.js";
import { proposedEvent } from "./semanticEventBuilder.js";

interface TraceRow {
  step_seq: number;
  tool_call_id: string;
  tool_name: string;
  tool_kind: string;
  param_summary: Record<string, unknown>;
  resource_hint: string | null;
  status: RuntimeTraceEvent["status"];
  result_preview: string | null;
  result_hash: string | null;
}

export interface AssembledTrace {
  events: RuntimeTraceEvent[];
  trace_completeness: "complete" | "missing_steps" | "previous_observation_pending";
}

export async function assembleTrace(request: AuditRequest): Promise<AssembledTrace> {
  const result = await pool.query<TraceRow>(
    `SELECT tc.step_seq, tc.tool_call_id, tc.tool_name, tc.tool_kind, tc.param_summary,
            tc.resource_hint, tc.status,
            latest.result_preview, latest.result_hash
       FROM tool_calls tc
       LEFT JOIN LATERAL (
         SELECT tr.result_preview, tr.result_hash
           FROM tool_results tr
          WHERE tr.tool_call_id = tc.tool_call_id
          ORDER BY tr.occurred_at DESC LIMIT 1
       ) latest ON TRUE
      WHERE tc.run_id = $1 AND tc.step_seq IS NOT NULL AND tc.step_seq < $2
      ORDER BY tc.step_seq ASC`,
    [request.run_id, request.step_seq ?? Number.MAX_SAFE_INTEGER],
  );
  const events: RuntimeTraceEvent[] = result.rows.map((row) => ({
    step_id: row.step_seq,
    tool_name: row.tool_name,
    tool_kind: row.tool_kind,
    args: row.param_summary,
    ...(row.resource_hint ? { target_resource_hint: row.resource_hint } : {}),
    observation: row.result_preview,
    observation_hash: row.result_hash,
    status: row.status,
  }));
  events.push(proposedEvent(request));
  return assembleTraceFromEvents(events);
}

export function assembleTraceFromEvents(events: RuntimeTraceEvent[]): AssembledTrace {
  const ordered = [...events].sort((left, right) => left.step_id - right.step_id);
  let completeness: AssembledTrace["trace_completeness"] = "complete";
  for (let index = 0; index < ordered.length; index += 1) {
    if (ordered[index]?.step_id !== index + 1) completeness = "missing_steps";
  }
  if (
    completeness === "complete" &&
    ordered.slice(0, -1).some((event) => event.status === "pending" || (event.status === "completed" && !event.observation_hash))
  ) {
    completeness = "previous_observation_pending";
  }
  return { events: ordered, trace_completeness: completeness };
}
