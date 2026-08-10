import "dotenv/config";
import { z } from "zod";

const booleanString = z
  .enum(["true", "false"])
  .default("false")
  .transform((value) => value === "true");

const environmentSchema = z.object({
  TRACESHIELD_DATABASE_URL: z.string().url(),
  TRACESHIELD_CORE_PORT: z.coerce.number().int().min(1).max(65_535).default(8787),
  TRACESHIELD_SAVE_RAW_PAYLOAD: booleanString,
  TRACESHIELD_SAVE_RAW_PARAMS: booleanString,
  TRACESHIELD_SAVE_RAW_RESULT: booleanString,
  TRACESHIELD_ENGINE_MODE: z.enum(["legacy", "shadow", "enforce"]).default("shadow"),
  TRACESHIELD_METHOD_PROFILE: z.string().default("balanced"),
  TRACESHIELD_METHOD_PROFILE_VERSION: z.string().default("balanced-v1"),
  TRACESHIELD_METHOD_VERSION: z.string().default("phase0-baseline"),
  TRACESHIELD_METHOD_TIMEOUT_MS: z.coerce.number().int().positive().default(120),
  TRACESHIELD_METHOD_QUEUE_LIMIT: z.coerce.number().int().positive().default(256),
  TRACESHIELD_METHOD_PYTHON: z.string().default("./method-engine/.venv/bin/python"),
  TRACESHIELD_METHOD_WORKER: z.string().default("./method-engine/python/traceshield_method/worker.py"),
  TRACESHIELD_ASSISTANT_BASE_URL: z.string().url().default("http://127.0.0.1:8790"),
  TRACESHIELD_ASSISTANT_TIMEOUT_MS: z.coerce.number().int().positive().default(60_000),
});

const environment = environmentSchema.parse(process.env);

export const config = {
  databaseUrl: environment.TRACESHIELD_DATABASE_URL,
  port: environment.TRACESHIELD_CORE_PORT,
  saveRawPayload: environment.TRACESHIELD_SAVE_RAW_PAYLOAD,
  saveRawParams: environment.TRACESHIELD_SAVE_RAW_PARAMS,
  saveRawResult: environment.TRACESHIELD_SAVE_RAW_RESULT,
  engineMode: environment.TRACESHIELD_ENGINE_MODE,
  methodProfile: environment.TRACESHIELD_METHOD_PROFILE,
  methodProfileVersion: environment.TRACESHIELD_METHOD_PROFILE_VERSION,
  methodVersion: environment.TRACESHIELD_METHOD_VERSION,
  methodTimeoutMs: environment.TRACESHIELD_METHOD_TIMEOUT_MS,
  methodQueueLimit: environment.TRACESHIELD_METHOD_QUEUE_LIMIT,
  methodPython: environment.TRACESHIELD_METHOD_PYTHON,
  methodWorker: environment.TRACESHIELD_METHOD_WORKER,
  assistantBaseUrl: environment.TRACESHIELD_ASSISTANT_BASE_URL,
  assistantTimeoutMs: environment.TRACESHIELD_ASSISTANT_TIMEOUT_MS,
  version: "0.1.0",
} as const;

export type CoreConfig = typeof config;
