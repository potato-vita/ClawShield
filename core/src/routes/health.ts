import type { FastifyInstance } from "fastify";
import { config } from "../config.js";
import { pool } from "../db/pool.js";

export async function registerHealthRoutes(app: FastifyInstance): Promise<void> {
  const healthHandler = async () => {
    let dbConnected = false;
    try {
      await pool.query("SELECT 1");
      dbConnected = true;
    } catch {
      dbConnected = false;
    }

    return {
      ok: dbConnected,
      version: config.version,
      db_connected: dbConnected,
    };
  };

  app.get("/health", healthHandler);
  app.get("/v1/health", healthHandler);
}
