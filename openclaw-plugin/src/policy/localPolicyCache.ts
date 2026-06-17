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
    // 没有 resource_hint 时使用空字符串而非通配符，避免不同资源共用同一 key
    const hint = request.resource_hint ?? "";
    return `${request.tool_kind}:${hint}`;
  }
}

export const defaultLocalPolicyCache = new LocalPolicyCache();
