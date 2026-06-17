import type { AuditRequest } from "../types/event.js";

export class LocalPolicyCache {
  private readonly allowKeys = new Set<string>();

  allow(request: Pick<AuditRequest, "tool_kind" | "resource_hint">): void {
    this.allowKeys.add(this.key(request));
  }

  hasAllow(request: Pick<AuditRequest, "tool_kind" | "resource_hint">): boolean {
    return this.allowKeys.has(this.key(request));
  }

  private key(request: Pick<AuditRequest, "tool_kind" | "resource_hint">): string {
    return `${request.tool_kind}:${request.resource_hint ?? "*"}`;
  }
}

export const defaultLocalPolicyCache = new LocalPolicyCache();
