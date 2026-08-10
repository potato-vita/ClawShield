import Fastify, { type FastifyInstance } from "fastify";
import { pathToFileURL } from "node:url";
import { config } from "./config.js";
import { closePool } from "./db/pool.js";
import { registerAuditRoutes } from "./routes/audit.js";
import { registerDashboardRoutes } from "./routes/dashboard.js";
import { registerEventRoutes } from "./routes/events.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerQueryRoutes } from "./routes/queries.js";
import { registerStreamRoutes } from "./routes/stream.js";
import { registerMethodRoutes } from "./routes/method.js";
import { registerAssistantRoutes } from "./routes/assistant.js";
import { methodShadowService } from "./services/methodShadowService.js";

export function buildServer(): FastifyInstance {
  const app = Fastify({ logger: true });

  app.addHook("onRequest", async (request, reply) => {
    reply.header("Access-Control-Allow-Origin", "*");
    reply.header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS");
    reply.header("Access-Control-Allow-Headers", "Content-Type,Accept,Last-Event-ID");
    if (request.method === "OPTIONS") {
      return reply.code(204).send();
    }
  });

  app.register(registerHealthRoutes);
  app.register(registerDashboardRoutes);
  app.register(registerAuditRoutes);
  app.register(registerEventRoutes);
  app.register(registerQueryRoutes);
  app.register(registerStreamRoutes);
  app.register(registerMethodRoutes);
  app.register(registerAssistantRoutes);

  app.setNotFoundHandler(async (_request, reply) => {
    return reply.code(404).send({ error: "not_found" });
  });

  app.setErrorHandler(async (error, request, reply) => {
    request.log.error(error);
    return reply.code(500).send({
      error: "internal_server_error",
      message: "TraceShield Core could not process the request.",
    });
  });

  app.addHook("onClose", async () => {
    await methodShadowService.stop();
    await closePool();
  });
  return app;
}

async function start(): Promise<void> {
  const app = buildServer();
  await methodShadowService.start();
  await app.listen({ host: "0.0.0.0", port: config.port });
}

const entrypoint = process.argv[1];
if (entrypoint && import.meta.url === pathToFileURL(entrypoint).href) {
  start().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
