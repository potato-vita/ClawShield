import type { EventClient } from "../client/eventClient.js";
import type { Logger } from "../logger.js";
import { DiskQueue } from "../queue/diskQueue.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import type { TraceEvent } from "../types/event.js";

export interface FlushWorkerOptions {
  memoryQueue: MemoryQueue<TraceEvent>;
  diskQueue: DiskQueue;
  eventClient: EventClient;
  logger: Logger;
  intervalMs: number;
  batchSize?: number;
}

export class FlushWorker {
  private timer: ReturnType<typeof setInterval> | undefined;
  private running = false;
  private readonly batchSize: number;

  constructor(private readonly options: FlushWorkerOptions) {
    this.batchSize = options.batchSize ?? 100;
  }

  start(): void {
    if (this.timer) {
      return;
    }

    this.timer = setInterval(() => {
      void this.flushOnce();
    }, this.options.intervalMs);
  }

  stop(): void {
    if (!this.timer) {
      return;
    }

    clearInterval(this.timer);
    this.timer = undefined;
  }

  async flushOnce(): Promise<void> {
    if (this.running) {
      return;
    }

    this.running = true;
    let memoryEvents: TraceEvent[] = [];
    try {
      const memoryItems = this.options.memoryQueue.dequeueBatch(this.batchSize);
      memoryEvents = memoryItems.map((item) => item.value);
      const diskEvents = await this.options.diskQueue.readBatch(
        Math.max(0, this.batchSize - memoryEvents.length),
      );
      const events = [...diskEvents, ...memoryEvents];

      if (events.length === 0) {
        return;
      }

      await this.options.eventClient.sendBatch(events);
      await this.options.diskQueue.deleteMany(diskEvents);
      this.options.logger.debug("TraceShield events flushed", {
        count: events.length,
      });
    } catch (error) {
      const queuedItems = this.options.memoryQueue.drain();
      const allEvents = [...memoryEvents, ...queuedItems.map((item) => item.value)];

      if (allEvents.length > 0) {
        try {
          await this.options.diskQueue.enqueueMany(allEvents);
          this.options.logger.warn("TraceShield event flush failed; events persisted to disk", {
            reason: error instanceof Error ? error.message : String(error),
            persisted: allEvents.length,
          });
        } catch (diskError) {
          // 磁盘写入也失败时，将事件放回内存队列避免丢失
          this.options.memoryQueue.requeue(
            allEvents.map((value) => ({
              id: value.event_id,
              value,
              attempts: 0,
              enqueued_at: Date.now(),
            })),
          );
          this.options.logger.error(
            "TraceShield event flush and disk persist both failed; events requeued",
            {
              flushError: error instanceof Error ? error.message : String(error),
              diskError: diskError instanceof Error ? diskError.message : String(diskError),
              requeued: allEvents.length,
            },
          );
        }
      } else {
        this.options.logger.warn("TraceShield event flush failed", {
          reason: error instanceof Error ? error.message : String(error),
        });
      }
    } finally {
      this.running = false;
    }
  }
}
