import { createHash } from "node:crypto";

export function sha256(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return createHash("sha256").update(text).digest("hex");
}

export function shortHash(value: unknown): string {
  return sha256(value).slice(0, 16);
}
