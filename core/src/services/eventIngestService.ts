import type { PoolClient } from "pg";
import { config } from "../config.js";
import { withTransaction } from "../db/pool.js";
import type { TraceEvent, TraceEventType } from "../types/pluginContract.js";
import { completeRun } from "./runLifecycleService.js";
import { applyPendingObservationDetection } from "./observationDetectionService.js";

const messageEventTypes = new Set<TraceEventType>([
  "message_received",
  "llm_input",
  "llm_output",
  "message_sending",
  "agent_end",
]);

export interface EventIngestResult {
  ok: true;
  inserted: number;
  duplicated: number;
  message_extracted: number;
  tool_result_extracted: number;
  insertedEvents: TraceEvent[];
}

export async function ingestEvents(events: TraceEvent[]): Promise<EventIngestResult> {
  return withTransaction(async (client) => {
    let inserted = 0;
    let duplicated = 0;
    let messageExtracted = 0;
    let toolResultExtracted = 0;
    const insertedEvents: TraceEvent[] = [];

    for (const event of events) {
      await upsertEventRun(client, event);
      const eventResult = await client.query<{ event_id: string }>(
        `INSERT INTO trace_events (
           event_id, schema_version, event_type, occurred_at, plugin_id, gateway_id,
           session_id, run_id, trace_id, mode, raw_payload
         ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
         ON CONFLICT (event_id) DO NOTHING
         RETURNING event_id`,
        [
          event.event_id,
          event.schema_version,
          event.type,
          new Date(event.timestamp),
          event.plugin_id,
          event.gateway_id ?? null,
          event.session_id,
          event.run_id,
          event.trace_id,
          event.mode,
          config.saveRawPayload ? JSON.stringify(event.payload) : null,
        ],
      );

      if (eventResult.rowCount === 0) {
        duplicated += 1;
        continue;
      }

      inserted += 1;
      insertedEvents.push(event);

      if (messageEventTypes.has(event.type)) {
        await extractMessage(client, event);
        messageExtracted += 1;
      }

      if (event.type === "after_tool_call") {
        await extractToolResult(client, event);
        toolResultExtracted += 1;
      }
      if (event.type === "agent_end") {
        await completeRun(client, event.run_id, new Date(event.timestamp));
      }
    }

    return {
      ok: true,
      inserted,
      duplicated,
      message_extracted: messageExtracted,
      tool_result_extracted: toolResultExtracted,
      insertedEvents,
    };
  });
}

async function upsertEventRun(client: PoolClient, event: TraceEvent): Promise<void> {
  const occurredAt = new Date(event.timestamp);
  await client.query(
    `INSERT INTO audit_sessions (session_id, first_seen_at, last_seen_at)
     VALUES ($1, $2, $2)
     ON CONFLICT (session_id) DO UPDATE SET
       last_seen_at = GREATEST(audit_sessions.last_seen_at, EXCLUDED.last_seen_at)`,
    [event.session_id, occurredAt],
  );
  await client.query(
    `INSERT INTO audit_runs (run_id, session_id, trace_id, started_at, last_seen_at)
     VALUES ($1, $2, $3, $4, $4)
     ON CONFLICT (run_id) DO UPDATE SET
       session_id = EXCLUDED.session_id,
       trace_id = EXCLUDED.trace_id,
       last_seen_at = GREATEST(audit_runs.last_seen_at, EXCLUDED.last_seen_at)`,
    [event.run_id, event.session_id, event.trace_id, occurredAt],
  );
}

async function extractMessage(client: PoolClient, event: TraceEvent): Promise<void> {
  const payload = event.payload;
  await client.query(
    `INSERT INTO messages (
       event_id, message_id, session_id, run_id, trace_id, event_type, role,
       content_preview, content_hash, summary, metadata, occurred_at
     ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12)
     ON CONFLICT (event_id) DO NOTHING`,
    [
      event.event_id,
      readString(payload.message_id),
      event.session_id,
      event.run_id,
      event.trace_id,
      event.type,
      readString(payload.role),
      previewValue(payload.content),
      readString(payload.content_hash),
      toJson(payload.summary),
      toJson(payload.metadata),
      new Date(event.timestamp),
    ],
  );
}

async function extractToolResult(client: PoolClient, event: TraceEvent): Promise<void> {
  const payload = event.payload;
  const toolCallId = readString(payload.tool_call_id) ?? `unknown_${event.event_id}`;
  const existing = await client.query<{ tool_call_id: string }>(
    "SELECT tool_call_id FROM tool_calls WHERE tool_call_id = $1",
    [toolCallId],
  );
  const placeholder = existing.rowCount === 0;

  if (placeholder) {
    await client.query(
      `INSERT INTO tool_calls (
         tool_call_id, session_id, run_id, trace_id, tool_name, tool_kind,
         step_seq, correlation_source, param_summary, resource_hint, risk_hint,
         status, started_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, NULL, $10, 'unknown', $11, NOW())
       ON CONFLICT (tool_call_id) DO NOTHING`,
      [
        toolCallId,
        event.session_id,
        event.run_id,
        event.trace_id,
        readString(payload.tool_name) ?? "unknown",
        readString(payload.tool_kind) ?? "unknown",
        readPositiveInteger(payload.step_seq),
        readString(payload.correlation_source),
        JSON.stringify(asRecord(payload.param_summary)),
        readString(payload.risk_hint),
        new Date(event.timestamp),
      ],
    );
  }

  const rawResult = payload.raw_result ?? payload.result ?? null;
  await client.query(
    `INSERT INTO tool_results (
       event_id, tool_call_id, result_preview, result_hash, result_summary,
       error_data, raw_result, duration_ms, occurred_at
     ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9)
     ON CONFLICT (event_id) DO NOTHING`,
    [
      event.event_id,
      toolCallId,
      previewValue(payload.result_preview),
      readString(payload.result_hash),
      toJson(payload.result_summary),
      toJson(payload.error),
      config.saveRawResult ? toJson(rawResult) : null,
      readNonNegativeInteger(payload.duration_ms),
      new Date(event.timestamp),
    ],
  );
  await applyPendingObservationDetection(client, toolCallId);

  if (!placeholder) {
    await client.query(
      `UPDATE tool_calls
          SET status = $2, updated_at = NOW()
        WHERE tool_call_id = $1`,
      [toolCallId, hasError(payload.error) ? "error" : "completed"],
    );
  }
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function readNonNegativeInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function readPositiveInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : null;
}

function previewValue(value: unknown): string | null {
  if (value === undefined || value === null) {
    return null;
  }
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.slice(0, 4_000);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function toJson(value: unknown): string | null {
  return value === undefined || value === null ? null : JSON.stringify(value);
}

function hasError(value: unknown): boolean {
  return value !== undefined && value !== null && value !== false;
}
