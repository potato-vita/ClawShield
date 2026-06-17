import type { AuditDecision } from "../types/decision.js";
import type { AuditRequest } from "../types/event.js";

export interface AuditClientOptions {
  baseUrl: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

export class AuditClient {
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly options: AuditClientOptions) {
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async auditToolCall(request: AuditRequest): Promise<AuditDecision> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs);

    try {
      const response = await this.fetchImpl(
        new URL("/v1/audit/tool-call", this.options.baseUrl),
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify(request),
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        throw new Error(`Core audit failed with HTTP ${response.status}`);
      }

      return parseAuditDecision(await response.json());
    } finally {
      clearTimeout(timeout);
    }
  }
}

export function parseAuditDecision(value: unknown): AuditDecision {
  if (value === null || typeof value !== "object") {
    throw new Error("Invalid audit decision: expected object");
  }

  const input = value as Record<string, unknown>;
  const decision = input.decision;
  const riskLevel = input.risk_level;
  const reason = input.reason;
  const matchedRules = input.matched_rules;

  if (!["ALLOW", "WARN", "ASK", "BLOCK"].includes(String(decision))) {
    throw new Error("Invalid audit decision: unsupported decision");
  }

  if (!["low", "medium", "high", "critical"].includes(String(riskLevel))) {
    throw new Error("Invalid audit decision: unsupported risk_level");
  }

  if (typeof reason !== "string") {
    throw new Error("Invalid audit decision: reason must be string");
  }

  if (!Array.isArray(matchedRules) || !matchedRules.every((item) => typeof item === "string")) {
    throw new Error("Invalid audit decision: matched_rules must be string[]");
  }

  return value as AuditDecision;
}
