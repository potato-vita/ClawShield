import type { FastifyInstance } from "fastify";
import { getRuntimeStatus } from "../services/statsService.js";

export async function registerDashboardRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/dashboard/runtime-status", async () => getRuntimeStatus());
}
