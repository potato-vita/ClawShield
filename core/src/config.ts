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
});

const environment = environmentSchema.parse(process.env);

export const config = {
  databaseUrl: environment.TRACESHIELD_DATABASE_URL,
  port: environment.TRACESHIELD_CORE_PORT,
  saveRawPayload: environment.TRACESHIELD_SAVE_RAW_PAYLOAD,
  saveRawParams: environment.TRACESHIELD_SAVE_RAW_PARAMS,
  saveRawResult: environment.TRACESHIELD_SAVE_RAW_RESULT,
  version: "0.1.0",
} as const;

export type CoreConfig = typeof config;
