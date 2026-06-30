import { MemoryQueue } from "../queue/memoryQueue.js";
import type { TraceEvent } from "../types/event.js";

interface SharedEventRuntime {
  queue: MemoryQueue<TraceEvent>;
}

const runtimeKey = Symbol.for("@traceshield/openclaw-plugin/event-runtime");

/**
 * OpenClaw may register a plugin more than once in the same process: once for
 * gateway services and again while building an agent turn. The queue must be
 * process-wide so hooks and the gateway-owned flush worker observe the same
 * events across those registrations.
 */
export function getSharedEventQueue(maxEvents: number): MemoryQueue<TraceEvent> {
  const globalStore = globalThis as unknown as Record<PropertyKey, unknown>;
  const existing = globalStore[runtimeKey] as SharedEventRuntime | undefined;
  if (existing) {
    return existing.queue;
  }

  const runtime: SharedEventRuntime = {
    queue: new MemoryQueue<TraceEvent>(maxEvents),
  };
  globalStore[runtimeKey] = runtime;
  return runtime.queue;
}
