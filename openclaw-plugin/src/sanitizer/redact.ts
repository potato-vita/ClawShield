import { sha256 } from "./hash.js";
import { previewText } from "./preview.js";

const sensitiveKeyPattern = /(?:token|api[_-]?key|password|passwd|secret|cookie|authorization|private[_-]?key)/i;
const apiKeyPattern = /\b(?:sk-[A-Za-z0-9_-]{16,}|[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,})\b/g;
const privateKeyPattern = /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g;
const assignmentSecretPattern = /\b(token|api[_-]?key|password|passwd|secret|cookie)\s*=\s*([^\s]+)/gi;

export function redactText(value: string): string {
  return previewText(value)
    .replace(privateKeyPattern, "[REDACTED_PRIVATE_KEY]")
    .replace(apiKeyPattern, (match) => `[REDACTED_HASH:${sha256(match).slice(0, 16)}]`)
    .replace(assignmentSecretPattern, "$1=[REDACTED]");
}

export function redactObject<T>(value: T): T {
  return redactUnknown(value) as T;
}

function redactUnknown(value: unknown): unknown {
  if (typeof value === "string") {
    return redactText(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => redactUnknown(item));
  }

  if (value !== null && typeof value === "object") {
    const redacted: Record<string, unknown> = {};
    for (const [key, nestedValue] of Object.entries(value as Record<string, unknown>)) {
      if (sensitiveKeyPattern.test(key)) {
        redacted[key] = hashSensitiveValue(nestedValue);
        continue;
      }

      redacted[key] = redactUnknown(nestedValue);
    }

    return redacted;
  }

  return value;
}

function hashSensitiveValue(value: unknown): Record<string, string> {
  return {
    redacted: "true",
    hash: sha256(value).slice(0, 16),
  };
}
