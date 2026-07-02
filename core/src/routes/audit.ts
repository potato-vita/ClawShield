import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { auditToolCall } from "../services/auditService.js";
import { auditEventStream } from "../services/streamService.js";
import type { AuditRequest } from "../types/pluginContract.js";

const identifier = z.string().min(1).max(300);
const auditRequestSchema = z.object({
  request_id: identifier,
  schema_version: z.literal("v1"),
  session_id: identifier,
  run_id: identifier,
  trace_id: identifier,
  tool_call_id: identifier,
  step_seq: z.number().int().positive().optional(),
  semantic_schema_version: z.literal("v1").optional(),
  correlation_source: z.string().max(100).optional(),
  tool_name: identifier,
  tool_kind: identifier,
  raw_params: z.record(z.unknown()),
  param_summary: z.record(z.unknown()),
  resource_hint: z.string().max(2_000).optional(),
  risk_hint: z.string().max(300).optional(),
  context: z.object({
    user_goal: z.string().max(4_000).optional(),
    recent_message_hashes: z.array(z.string().max(300)).max(100).optional(),
    workspace_root: z.string().max(2_000).optional(),
  }),
});

export async function registerAuditRoutes(app: FastifyInstance): Promise<void> {
  app.post("/v1/audit/tool-call", async (request, reply) => {
    const parsed = auditRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({
        error: "invalid_audit_request",
        details: parsed.error.flatten(),
      });
    }

    const data = parsed.data;
    const auditRequest: AuditRequest = {
      request_id: data.request_id,
      schema_version: data.schema_version,
      session_id: data.session_id,
      run_id: data.run_id,
      trace_id: data.trace_id,
      tool_call_id: data.tool_call_id,
      ...(data.step_seq !== undefined ? { step_seq: data.step_seq } : {}),
      ...(data.semantic_schema_version !== undefined
        ? { semantic_schema_version: data.semantic_schema_version }
        : {}),
      ...(data.correlation_source !== undefined
        ? { correlation_source: data.correlation_source }
        : {}),
      tool_name: data.tool_name,
      tool_kind: data.tool_kind,
      raw_params: data.raw_params,
      param_summary: data.param_summary,
      ...(data.resource_hint !== undefined ? { resource_hint: data.resource_hint } : {}),
      ...(data.risk_hint !== undefined ? { risk_hint: data.risk_hint } : {}),
      context: {
        ...(data.context.user_goal !== undefined ? { user_goal: data.context.user_goal } : {}),
        ...(data.context.recent_message_hashes !== undefined
          ? { recent_message_hashes: data.context.recent_message_hashes }
          : {}),
        ...(data.context.workspace_root !== undefined
          ? { workspace_root: data.context.workspace_root }
          : {}),
      },
    };
    const decision = await auditToolCall(auditRequest);
    auditEventStream.publish("audit_event", {
      request_id: auditRequest.request_id,
      session_id: auditRequest.session_id,
      run_id: auditRequest.run_id,
      trace_id: auditRequest.trace_id,
      tool_call_id: auditRequest.tool_call_id,
      tool_name: auditRequest.tool_name,
      tool_kind: auditRequest.tool_kind,
      decision: decision.decision,
      risk_level: decision.risk_level,
      reason: decision.reason,
      matched_rules: decision.matched_rules,
      engine: decision.engine ?? null,
      engine_version: decision.engine_version ?? null,
    });
    return decision;
  });
}
