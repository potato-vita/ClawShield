import type { HookContext } from "../types/hook.js";
import { createId } from "../utils/id.js";

export interface NormalizedContext {
  session_id: string;
  run_id: string;
  trace_id: string;
  workspace_root?: string;
  user_goal?: string;
  recent_message_hashes?: string[];
}

export function normalizeContext(input: HookContext): NormalizedContext {
  const context: NormalizedContext = {
    session_id: input.session_id ?? createId("session"),
    run_id: input.run_id ?? createId("run"),
    trace_id: input.trace_id ?? createId("trace"),
  };

  if (input.workspace_root !== undefined) {
    context.workspace_root = input.workspace_root;
  }

  if (input.user_goal !== undefined) {
    context.user_goal = input.user_goal;
  }

  if (input.recent_message_hashes !== undefined) {
    context.recent_message_hashes = input.recent_message_hashes;
  }

  return context;
}
