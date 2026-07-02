import { z } from "zod";

export interface MethodRequest {
  protocol_version: "v1";
  request_id: string;
  method: "health" | "evaluate_runtime_trace" | "detect_observation" | "shutdown";
  params?: Record<string, unknown>;
}

const responseSchema = z.object({
  protocol_version: z.literal("v1"),
  request_id: z.string(),
  ok: z.boolean(),
  result: z.record(z.unknown()).optional(),
  error: z.object({ code: z.string(), message: z.string() }).optional(),
});

export type MethodResponse = z.infer<typeof responseSchema>;

export function parseMethodResponse(line: string): MethodResponse {
  return responseSchema.parse(JSON.parse(line));
}
