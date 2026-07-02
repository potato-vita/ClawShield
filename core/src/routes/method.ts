import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { pool } from "../db/pool.js";
import { methodShadowService } from "../services/methodShadowService.js";

const idParams = z.object({ id: z.string().min(1) });
const runParams = z.object({ runId: z.string().min(1) });

export async function registerMethodRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/method/status", async () => methodShadowService.status());

  app.post("/v1/method/observation", async (request, reply) => {
    const parsed = z.object({
      event_id: z.string().min(1),
      session_id: z.string().min(1),
      run_id: z.string().min(1),
      trace_id: z.string().min(1),
      tool_call_id: z.string().min(1),
      step_seq: z.number().int().positive(),
      observation: z.unknown(),
      observation_hash: z.string().optional(),
    }).safeParse(request.body);
    if (!parsed.success || !("observation" in parsed.data)) {
      return reply.code(400).send({ error: "invalid_observation" });
    }
    const result = await methodShadowService.detectObservation({
      run_id: parsed.data.run_id,
      tool_call_id: parsed.data.tool_call_id,
      step_seq: parsed.data.step_seq,
      observation: parsed.data.observation,
      ...(parsed.data.observation_hash !== undefined
        ? { observation_hash: parsed.data.observation_hash }
        : {}),
    });
    return { ok: true, ...result };
  });

  app.get("/v1/method/evaluations", async (request, reply) => {
    const parsed = z.coerce.number().int().min(1).max(200).default(50).safeParse(
      (request.query as { limit?: unknown }).limit,
    );
    if (!parsed.success) return reply.code(400).send({ error: "invalid_limit" });
    const result = await pool.query(
      `SELECT method_evaluation_id::text, request_id, tool_call_id, run_id, step_seq,
              profile, profile_version, method_version, status, method_decision,
              runtime_suggestion, risk_level, latency_ms, diff_type, trace_completeness,
              error_code, error_message, evaluation_revision, created_at, completed_at
         FROM method_evaluations ORDER BY created_at DESC LIMIT $1`,
      [parsed.data],
    );
    return { evaluations: result.rows, limit: parsed.data };
  });

  app.get("/v1/method/evaluations/:id", async (request, reply) => {
    const parsed = idParams.safeParse(request.params);
    if (!parsed.success) return reply.code(400).send({ error: "invalid_id" });
    const evaluation = await pool.query(
      "SELECT * FROM method_evaluations WHERE method_evaluation_id = $1",
      [parsed.data.id],
    );
    if (!evaluation.rows[0]) return reply.code(404).send({ error: "method_evaluation_not_found" });
    const [violations, graph] = await Promise.all([
      pool.query("SELECT * FROM method_violations WHERE method_evaluation_id = $1 ORDER BY created_at", [parsed.data.id]),
      pool.query("SELECT * FROM method_graph_snapshots WHERE method_evaluation_id = $1", [parsed.data.id]),
    ]);
    return { evaluation: evaluation.rows[0], violations: violations.rows, graph: graph.rows[0] ?? null };
  });

  app.get("/v1/runs/:runId/method-graph", async (request, reply) => {
    const parsed = runParams.safeParse(request.params);
    if (!parsed.success) return reply.code(400).send({ error: "invalid_run_id" });
    const result = await pool.query(
      `SELECT me.method_evaluation_id::text, mgs.nodes, mgs.edges
         FROM method_evaluations me
         JOIN method_graph_snapshots mgs USING (method_evaluation_id)
        WHERE me.run_id=$1 AND me.status='ok'
        ORDER BY me.evaluation_revision DESC, me.completed_at DESC LIMIT 1`,
      [parsed.data.runId],
    );
    const graph = result.rows[0];
    if (!graph) return reply.code(404).send({ error: "method_graph_not_found" });
    return { run_id: parsed.data.runId, ...graph };
  });

  app.get("/v1/runs/:runId/decision-diff", async (request) => {
    const parsed = runParams.parse(request.params);
    const result = await pool.query(
      `SELECT method_evaluation_id::text, request_id, tool_call_id, step_seq,
              status, runtime_suggestion, diff_type, latency_ms, created_at
         FROM method_evaluations WHERE run_id=$1 ORDER BY step_seq, created_at`,
      [parsed.runId],
    );
    return { run_id: parsed.runId, evaluations: result.rows };
  });
}
