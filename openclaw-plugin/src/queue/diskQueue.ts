import { mkdir, readdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import type { TraceEvent } from "../types/event.js";

export class DiskQueue {
  constructor(private readonly dir: string) {}

  async enqueue(event: TraceEvent): Promise<void> {
    await mkdir(this.dir, { recursive: true });
    const finalPath = this.pathFor(event.event_id);
    const tempPath = `${finalPath}.tmp`;
    await writeFile(tempPath, JSON.stringify(event), "utf8");
    await rename(tempPath, finalPath);
  }

  async enqueueMany(events: TraceEvent[]): Promise<void> {
    for (const event of events) {
      await this.enqueue(event);
    }
  }

  async readBatch(limit: number): Promise<TraceEvent[]> {
    await mkdir(this.dir, { recursive: true });
    const files = (await readdir(this.dir))
      .filter((file) => file.endsWith(".json"))
      .sort()
      .slice(0, limit);

    const events: TraceEvent[] = [];
    for (const file of files) {
      const content = await readFile(join(this.dir, file), "utf8");
      events.push(JSON.parse(content) as TraceEvent);
    }

    return events;
  }

  async deleteMany(events: TraceEvent[]): Promise<void> {
    await Promise.all(events.map((event) => rm(this.pathFor(event.event_id), { force: true })));
  }

  private pathFor(eventId: string): string {
    return join(this.dir, `${eventId}.json`);
  }
}
