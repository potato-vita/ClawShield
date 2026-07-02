import type { MethodEngineClient } from "./methodEngineClient.js";

export async function getMethodEngineHealth(client: MethodEngineClient): Promise<Record<string, unknown>> {
  const startedAt = performance.now();
  const result = await client.health();
  return { ...result, round_trip_ms: performance.now() - startedAt };
}

