import { registerMessageHooks as registerHooks } from "../hooks/messageHooks.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type { HookRegistrar } from "./on.js";
import type { RunContextRegistry } from "../runtime/runContextRegistry.js";

export interface RegisterMessageHooksOptions {
  api: unknown;
  config: PluginConfig;
  queue: MemoryQueue<TraceEvent>;
  runContextRegistry: RunContextRegistry;
  on: HookRegistrar;
}

export function registerMessageHooks(options: RegisterMessageHooksOptions): void {
  registerHooks(options);
}
