import type { FastifyInstance } from "fastify";
import { auditEventStream } from "../services/streamService.js";

export async function registerStreamRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/stream/audit-events", async (request, reply) => {
    reply.hijack();
    const response = reply.raw;
    response.writeHead(200, {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    });
    response.write(
      `retry: 3000\nevent: connected\ndata: ${JSON.stringify({ ok: true })}\n\n`,
    );

    const removeClient = auditEventStream.add(response);
    const heartbeat = setInterval(() => {
      if (!response.destroyed && !response.writableEnded) {
        response.write(`: heartbeat ${Date.now()}\n\n`);
      }
    }, 15_000);

    request.raw.once("close", () => {
      clearInterval(heartbeat);
      removeClient();
    });
  });
}
