import type { AuditClient } from "../client/auditClient.js";
import { registerToolHooks as registerHooks } from "../hooks/toolHooks.js";
import type { Logger } from "../logger.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type { HookRegistrar } from "./on.js";

export interface RegisterToolHooksOptions {
  api: unknown;
  config: PluginConfig;
  queue: MemoryQueue<TraceEvent>;
  logger: Logger;
  auditClient: AuditClient;
  on: HookRegistrar;
}

export function registerToolHooks(options: RegisterToolHooksOptions): void {
  registerHooks(options);
}
