import { normalizeMessage } from "../events/normalizeMessage.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent, TraceEventType } from "../types/event.js";
import type { HookRegistry, RawMessageHookInput } from "../types/hook.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";

const messageEvents: Array<Extract<
  TraceEventType,
  "message_received" | "llm_input" | "llm_output" | "message_sending" | "agent_end"
>> = [
  "message_received",
  "llm_input",
  "llm_output",
  "message_sending",
  "agent_end",
];

export function registerMessageHooks(
  hooks: HookRegistry,
  queue: MemoryQueue<TraceEvent>,
  config: PluginConfig,
): void {
  for (const eventName of messageEvents) {
    hooks.on(eventName, (input) => {
      queue.enqueue(normalizeMessage(eventName, input as RawMessageHookInput, config));
    });
  }
}
