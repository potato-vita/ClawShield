import type { TraceEvent } from "../types/event.js";

export interface EventClientOptions {
  baseUrl: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

export class EventClient {
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly options: EventClientOptions) {
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async sendBatch(events: TraceEvent[]): Promise<void> {
    if (events.length === 0) {
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs);

    try {
      const response = await this.fetchImpl(
        new URL("/v1/events/batch", this.options.baseUrl),
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify({ events }),
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        throw new Error(`Core event flush failed with HTTP ${response.status}`);
      }
    } finally {
      clearTimeout(timeout);
    }
  }
}
