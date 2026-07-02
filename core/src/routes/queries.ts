import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { pool } from "../db/pool.js";
import { buildRiskGraph, RunNotFoundError } from "../services/riskGraphService.js";

const limitSchema = z.coerce.number().int().min(1).max(200).default(50);

interface IdParams {
  toolCallId?: string;
  runId?: string;
  sessionId?: string;
}

export async function registerQueryRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/audit/sessions", async (request, reply) => {
    const filter = (request.query as { filter?: unknown }).filter ?? "all";
    if (filter !== "all" && filter !== "risk") {
      return reply.code(400).send({ error: "invalid_filter" });
    }
    const result = await pool.query(
      `SELECT
         s.session_id, s.first_seen_at, s.last_seen_at,
         COALESCE(counts.run_count, 0)::int AS run_count,
         COALESCE(counts.message_count, 0)::int AS message_count,
         COALESCE(counts.tool_call_count, 0)::int AS tool_call_count,
         latest_run.run_id AS latest_run_id,
         latest_run.started_at AS latest_run_started_at,
         COALESCE(latest_run.risk_level, 'low') AS risk_level,
         COALESCE(latest_run.final_decision, 'ALLOW') AS final_decision,
         latest_event.event_type AS latest_event_type
       FROM audit_sessions s
       LEFT JOIN LATERAL (
         SELECT
           (SELECT COUNT(*) FROM audit_runs ar WHERE ar.session_id = s.session_id) AS run_count,
           (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS message_count,
           (SELECT COUNT(*) FROM tool_calls tc WHERE tc.session_id = s.session_id) AS tool_call_count
       ) counts ON TRUE
       LEFT JOIN LATERAL (
         SELECT ar.run_id, ar.started_at, ar.risk_level, ar.final_decision
         FROM audit_runs ar
         WHERE ar.session_id = s.session_id
         ORDER BY ar.last_seen_at DESC, ar.started_at DESC
         LIMIT 1
       ) latest_run ON TRUE
       LEFT JOIN LATERAL (
         SELECT te.event_type
         FROM trace_events te
         WHERE te.session_id = s.session_id
         ORDER BY te.occurred_at DESC
         LIMIT 1
       ) latest_event ON TRUE
       WHERE ($1::boolean = FALSE OR COALESCE(latest_run.risk_level, 'low') IN ('high', 'critical') OR latest_run.final_decision = 'BLOCK')
       ORDER BY s.last_seen_at DESC
       LIMIT 200`,
      [filter === "risk"],
    );
    return { sessions: result.rows, filter };
  });

  app.get("/v1/audit/sessions/:sessionId/runs", async (request, reply) => {
    const sessionId = (request.params as IdParams).sessionId ?? "";
    const session = await pool.query("SELECT 1 FROM audit_sessions WHERE session_id = $1", [sessionId]);
    if (session.rowCount === 0) {
      return reply.code(404).send({ error: "session_not_found" });
    }
    const result = await pool.query(
      `SELECT run_id, session_id, trace_id, started_at, last_seen_at,
              tool_call_count, blocked_count, warn_count, ask_count,
              risk_level, final_decision, status, ended_at, end_reason
       FROM audit_runs
       WHERE session_id = $1
       ORDER BY last_seen_at DESC, started_at DESC`,
      [sessionId],
    );
    return { session_id: sessionId, runs: result.rows };
  });

  app.get("/v1/audit/events", async (request, reply) => {
    const parsed = limitSchema.safeParse((request.query as { limit?: unknown }).limit);
    if (!parsed.success) {
      return reply.code(400).send({ error: "invalid_limit" });
    }

    const result = await pool.query(
      `SELECT
         tc.tool_call_id, tc.request_id, tc.session_id, tc.run_id, tc.trace_id,
         tc.tool_name, tc.tool_kind, tc.step_seq, tc.correlation_source,
         tc.resource_hint, tc.risk_hint, tc.status, tc.started_at,
         latest.decision, latest.risk_level, latest.reason, latest.matched_rules,
         latest.created_at AS decided_at
       FROM tool_calls tc
       LEFT JOIN LATERAL (
         SELECT ad.decision, ad.risk_level, ad.reason, ad.matched_rules, ad.created_at
         FROM audit_decisions ad
         WHERE ad.tool_call_id = tc.tool_call_id
         ORDER BY ad.created_at DESC
         LIMIT 1
       ) latest ON TRUE
       ORDER BY tc.started_at DESC, tc.tool_call_id DESC
       LIMIT $1`,
      [parsed.data],
    );
    return { events: result.rows, limit: parsed.data };
  });

  app.get("/v1/tool-calls/:toolCallId", async (request, reply) => {
    const toolCallId = (request.params as IdParams).toolCallId ?? "";
    const toolCall = await getToolCall(toolCallId);
    if (!toolCall) {
      return reply.code(404).send({ error: "tool_call_not_found" });
    }
    return { tool_call: toolCall };
  });

  app.get("/v1/tool-calls/:toolCallId/decision", async (request, reply) => {
    const toolCallId = (request.params as IdParams).toolCallId ?? "";
    const toolCall = await getToolCall(toolCallId);
    if (!toolCall) {
      return reply.code(404).send({ error: "tool_call_not_found" });
    }

    const decisionResult = await pool.query(
      `SELECT
         decision_id::text, request_id, tool_call_id, decision, risk_level, reason,
         matched_rules, policy_version, evidence_refs, modified_params, approval,
         fallback_used, engine, engine_version, method_evaluation_id, created_at
       FROM audit_decisions
       WHERE tool_call_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [toolCallId],
    );
    const decision = decisionResult.rows[0] ?? null;
    const ruleHits = decision
      ? await pool.query(
          `SELECT rule_hit_id::text, policy_id, matched, detail, created_at
           FROM audit_rule_hits
           WHERE decision_id = $1
           ORDER BY created_at ASC`,
          [decision.decision_id],
        )
      : { rows: [] };

    return { tool_call: toolCall, decision, rule_hits: ruleHits.rows };
  });

  app.get("/v1/runs/:runId/evidence-path", async (request, reply) => {
    const runId = (request.params as IdParams).runId ?? "";
    if (!(await runExists(runId))) {
      return reply.code(404).send({ error: "run_not_found" });
    }
    const result = await pool.query(
      `SELECT
         es.evidence_step_id::text, es.evidence_id::text, es.run_id, es.tool_call_id,
         es.step_order, es.step_type, es.title, es.detail, es.created_at,
         ei.evidence_type, ei.summary AS evidence_summary,
         ad.decision, ad.risk_level
       FROM evidence_steps es
       JOIN evidence_items ei ON ei.evidence_id = es.evidence_id
       LEFT JOIN audit_decisions ad ON ad.decision_id = ei.decision_id
       WHERE es.run_id = $1
       ORDER BY es.created_at ASC, es.step_order ASC`,
      [runId],
    );
    return { run_id: runId, steps: result.rows };
  });

  app.get("/v1/runs/:runId/risk-graph", async (request, reply) => {
    const runId = (request.params as IdParams).runId ?? "";
    try {
      return await buildRiskGraph(runId);
    } catch (error) {
      if (error instanceof RunNotFoundError) {
        return reply.code(404).send({ error: "run_not_found" });
      }
      throw error;
    }
  });

  app.get("/v1/runs/:runId/conversation-summary", async (request, reply) => {
    const runId = (request.params as IdParams).runId ?? "";
    if (!(await runExists(runId))) {
      return reply.code(404).send({ error: "run_not_found" });
    }
    const result = await pool.query(
      `SELECT message_row_id::text, event_id, event_type, role, summary, occurred_at
       FROM messages
       WHERE run_id = $1
       ORDER BY occurred_at ASC, created_at ASC
       LIMIT 200`,
      [runId],
    );
    return { run_id: runId, messages: result.rows };
  });
}

async function getToolCall(toolCallId: string): Promise<Record<string, unknown> | undefined> {
  const result = await pool.query(
    `SELECT
       tool_call_id, request_id, session_id, run_id, trace_id, tool_name, tool_kind,
       step_seq, correlation_source, param_summary, resource_hint, risk_hint,
       status, started_at, updated_at
     FROM tool_calls
     WHERE tool_call_id = $1`,
    [toolCallId],
  );
  return result.rows[0];
}

async function runExists(runId: string): Promise<boolean> {
  const result = await pool.query("SELECT 1 FROM audit_runs WHERE run_id = $1", [runId]);
  return result.rowCount !== 0;
}
