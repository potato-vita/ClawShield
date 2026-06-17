import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";

export interface RegisterStatusToolOptions {
  api: unknown;
  config: PluginConfig;
  queue: MemoryQueue<TraceEvent>;
}

export function registerStatusTool(options: RegisterStatusToolOptions): void {
  const { api, config, queue } = options;
  const typedApi = api as {
    registerTool: (tool: unknown) => void;
  };

  typedApi.registerTool({
    name: "traceshield_status",
    label: "TraceShield status",
    description:
      "Show TraceShield plugin status, Core URL, fallback mode, and local event queue size.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {},
    },
    execute: async () => ({
      content: [
        {
          type: "text",
          text: [
            "TraceShield Security Plugin is loaded.",
            `Core URL: ${config.core_base_url}`,
            `Audit timeout: ${config.audit_timeout_ms}ms`,
            `Fallback enabled: ${String(config.fallback_enabled)}`,
            `Debug full payload: ${String(config.debug_full_payload)}`,
            `Queued events: ${String(queue.size())}`,
          ].join("\n"),
        },
      ],
    }),
  } as never);
}
