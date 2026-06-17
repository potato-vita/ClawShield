import type { AuditDecision } from "./decision.js";

export interface HookRegistry {
  on(eventName: string, handler: (input: unknown) => unknown | Promise<unknown>): void;
}

export interface HookContext {
  session_id?: string;
  run_id?: string;
  trace_id?: string;
  workspace_root?: string;
  user_goal?: string;
  recent_message_hashes?: string[];
}

export interface RawMessageHookInput extends HookContext {
  message_id?: string;
  role?: string;
  content?: unknown;
  metadata?: Record<string, unknown>;
}

export interface RawToolCallHookInput extends HookContext {
  tool_call_id?: string;
  tool_name?: string;
  tool_kind?: string;
  params?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface RawToolResultHookInput extends RawToolCallHookInput {
  result?: unknown;
  error?: unknown;
  duration_ms?: number;
}

export interface OpenClawToolDecisionResult {
  block?: boolean;
  blockReason?: string;
  requireApproval?: {
    approvalId: string;
    title: string;
    description: string;
    defaultAction: "ALLOW" | "BLOCK";
    timeoutMs: number;
  };
  modifiedParams?: Record<string, unknown>;
  warning?: string;
  auditDecision?: AuditDecision;
}
