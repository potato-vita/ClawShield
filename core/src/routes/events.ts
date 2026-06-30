import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { ingestEvents } from "../services/eventIngestService.js";
import { auditEventStream } from "../services/streamService.js";
import type { TraceEvent } from "../types/pluginContract.js";

const eventSchema = z.object({
  event_id: z.string().min(1).max(300),
  schema_version: z.literal("v1"),
  type: z.enum([
    "message_received",
    "llm_input",
    "llm_output",
    "message_sending",
    "before_tool_call",
    "after_tool_call",
    "agent_end",
    "fallback_decision",
  ]),
  timestamp: z.number().int().nonnegative(),
  plugin_id: z.string().min(1).max(300),
  gateway_id: z.string().min(1).max(300).optional(),
  session_id: z.string().min(1).max(300),
  run_id: z.string().min(1).max(300),
  trace_id: z.string().min(1).max(300),
  mode: z.enum(["sync", "async"]),
  payload: z.record(z.unknown()),
});

const eventBatchSchema = z.object({
  events: z.array(eventSchema).max(1_000),
});

export async function registerEventRoutes(app: FastifyInstance): Promise<void> {
  app.post("/v1/events/batch", async (request, reply) => {
    const parsed = eventBatchSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({
        error: "invalid_event_batch",
        details: parsed.error.flatten(),
      });
    }

    const events: TraceEvent[] = parsed.data.events.map((event) => ({
      event_id: event.event_id,
      schema_version: event.schema_version,
      type: event.type,
      timestamp: event.timestamp,
      plugin_id: event.plugin_id,
      ...(event.gateway_id !== undefined ? { gateway_id: event.gateway_id } : {}),
      session_id: event.session_id,
      run_id: event.run_id,
      trace_id: event.trace_id,
      mode: event.mode,
      payload: event.payload,
    }));
    const result = await ingestEvents(events);
    for (const event of result.insertedEvents) {
      auditEventStream.publish("trace_event", {
        event_id: event.event_id,
        type: event.type,
        timestamp: event.timestamp,
        plugin_id: event.plugin_id,
        session_id: event.session_id,
        run_id: event.run_id,
        trace_id: event.trace_id,
      });
    }

    return {
      ok: result.ok,
      inserted: result.inserted,
      duplicated: result.duplicated,
      message_extracted: result.message_extracted,
      tool_result_extracted: result.tool_result_extracted,
    };
  });
}
