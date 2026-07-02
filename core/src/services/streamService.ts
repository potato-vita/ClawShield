import { randomUUID } from "node:crypto";
import type { ServerResponse } from "node:http";

class AuditEventStream {
  private readonly clients = new Set<ServerResponse>();

  add(client: ServerResponse): () => void {
    this.clients.add(client);
    return () => this.clients.delete(client);
  }

  publish(
    event:
      | "audit_event"
      | "trace_event"
      | "method_evaluation_queued"
      | "method_evaluation_completed"
      | "method_evaluation_failed",
    data: Record<string, unknown>,
  ): void {
    const payload = [
      `id: ${randomUUID()}`,
      `event: ${event}`,
      `data: ${JSON.stringify(data)}`,
      "",
      "",
    ].join("\n");

    for (const client of this.clients) {
      if (client.destroyed || client.writableEnded) {
        this.clients.delete(client);
        continue;
      }
      client.write(payload);
    }
  }

  get clientCount(): number {
    return this.clients.size;
  }
}

export const auditEventStream = new AuditEventStream();
