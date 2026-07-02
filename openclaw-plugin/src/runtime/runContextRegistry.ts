import type { HookContext, RawToolCallHookInput, RawToolResultHookInput } from "../types/hook.js";
import { createId } from "../utils/id.js";

export type CorrelationSource = "openclaw_id" | "generated_pending_match" | "unmatched";

export interface StableRunContext {
  session_id: string;
  run_id: string;
  trace_id: string;
}

export interface StableToolCallContext extends StableRunContext {
  tool_call_id: string;
  step_seq: number;
  correlation_source: CorrelationSource;
}

interface PendingCall extends StableToolCallContext {
  tool_name: string;
  completed: boolean;
}

interface RunState extends StableRunContext {
  key: string;
  next_step_seq: number;
  last_seen_at: number;
  ended: boolean;
  calls: Map<string, PendingCall>;
  pending: PendingCall[];
}

export interface RunContextRegistryOptions {
  now?: () => number;
  ttlMs?: number;
}

export class RunContextRegistry {
  private readonly runs = new Map<string, RunState>();
  private readonly explicitRunIndex = new Map<string, RunState>();
  private readonly now: () => number;
  private readonly ttlMs: number;

  constructor(options: RunContextRegistryOptions = {}) {
    this.now = options.now ?? Date.now;
    this.ttlMs = options.ttlMs ?? 30 * 60_000;
  }

  resolveRun(input: HookContext): StableRunContext {
    this.cleanup();
    const explicitRun = input.run_id ? this.explicitRunIndex.get(input.run_id) : undefined;
    if (explicitRun && !explicitRun.ended) {
      explicitRun.last_seen_at = this.now();
      return this.toStableRun(explicitRun);
    }
    const key = this.contextKey(input);
    const current = this.runs.get(key);
    if (current && !current.ended && (!input.run_id || current.run_id === input.run_id)) {
      current.last_seen_at = this.now();
      return this.toStableRun(current);
    }
    const state: RunState = {
      key,
      session_id: input.session_id ?? current?.session_id ?? createId("session"),
      run_id: input.run_id ?? createId("run"),
      trace_id: input.trace_id ?? createId("trace"),
      next_step_seq: 1,
      last_seen_at: this.now(),
      ended: false,
      calls: new Map(),
      pending: [],
    };
    this.runs.set(key, state);
    this.explicitRunIndex.set(state.run_id, state);
    return this.toStableRun(state);
  }

  beginToolCall(input: RawToolCallHookInput): StableToolCallContext {
    const run = this.getRunState(input);
    const existing = input.tool_call_id ? run.calls.get(input.tool_call_id) : undefined;
    if (existing) return { ...existing };
    const call: PendingCall = {
      ...this.toStableRun(run),
      tool_call_id: input.tool_call_id ?? createId("tool"),
      step_seq: run.next_step_seq++,
      correlation_source: input.tool_call_id ? "openclaw_id" : "generated_pending_match",
      tool_name: input.tool_name ?? "unknown",
      completed: false,
    };
    run.calls.set(call.tool_call_id, call);
    run.pending.push(call);
    return { ...call };
  }

  completeToolCall(input: RawToolResultHookInput): StableToolCallContext {
    const run = this.getRunState(input);
    let call = input.tool_call_id ? run.calls.get(input.tool_call_id) : undefined;
    call ??= run.pending.find(
      (candidate) => !candidate.completed && candidate.tool_name === (input.tool_name ?? "unknown"),
    );
    call ??= run.pending.find((candidate) => !candidate.completed);
    if (call) {
      call.completed = true;
      return {
        ...call,
        correlation_source: input.tool_call_id ? "openclaw_id" : "generated_pending_match",
      };
    }
    const unmatched: PendingCall = {
      ...this.toStableRun(run),
      tool_call_id: input.tool_call_id ?? createId("tool"),
      step_seq: run.next_step_seq++,
      correlation_source: "unmatched",
      tool_name: input.tool_name ?? "unknown",
      completed: true,
    };
    run.calls.set(unmatched.tool_call_id, unmatched);
    return { ...unmatched };
  }

  endRun(input: HookContext): void {
    const state = input.run_id
      ? this.explicitRunIndex.get(input.run_id)
      : this.runs.get(this.contextKey(input));
    if (state) {
      state.ended = true;
      state.last_seen_at = this.now();
    }
  }

  cleanup(): void {
    const cutoff = this.now() - this.ttlMs;
    for (const [key, state] of this.runs) {
      if (state.last_seen_at < cutoff) {
        this.runs.delete(key);
        this.explicitRunIndex.delete(state.run_id);
      }
    }
  }

  private getRunState(input: HookContext): RunState {
    const stable = this.resolveRun(input);
    const state = this.explicitRunIndex.get(stable.run_id);
    if (!state) throw new Error("Run context was not registered");
    return state;
  }

  private contextKey(input: HookContext): string {
    return [input.session_id ?? "generated-session", input.workspace_root ?? "no-workspace"].join("|");
  }

  private toStableRun(state: RunState): StableRunContext {
    return { session_id: state.session_id, run_id: state.run_id, trace_id: state.trace_id };
  }
}

const registryKey = Symbol.for("@traceshield/openclaw-plugin/run-context-registry");

export function getSharedRunContextRegistry(): RunContextRegistry {
  const store = globalThis as unknown as Record<PropertyKey, unknown>;
  const existing = store[registryKey];
  if (existing instanceof RunContextRegistry) return existing;
  const registry = new RunContextRegistry();
  store[registryKey] = registry;
  return registry;
}

