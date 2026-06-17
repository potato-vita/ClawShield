import { EventClient } from "../client/eventClient.js";
import { createLogger } from "../logger.js";
import { DiskQueue } from "../queue/diskQueue.js";
import type { MemoryQueue } from "../queue/memoryQueue.js";
import type { PluginConfig } from "../types/config.js";
import type { TraceEvent } from "../types/event.js";
import { FlushWorker } from "../worker/flushWorker.js";

export interface RegisterFlushWorkerOptions {
  api: unknown;
  config: PluginConfig;
  queue: MemoryQueue<TraceEvent>;
}

export function registerFlushWorker(options: RegisterFlushWorkerOptions): void {
  const { api, config, queue } = options;
  const typedApi = api as {
    registerService: (service: unknown) => void;
  };
  let flushWorker: FlushWorker | undefined;

  typedApi.registerService({
    id: "traceshield-event-flush-worker",
    start(ctx: { logger: { info: (message: string) => void } }) {
      const serviceLogger = createLogger("traceshield-flush-worker");
      flushWorker = new FlushWorker({
        memoryQueue: queue,
        diskQueue: new DiskQueue(config.disk_queue_dir),
        eventClient: new EventClient({
          baseUrl: config.core_base_url,
          timeoutMs: config.event_flush_timeout_ms,
        }),
        logger: serviceLogger,
        intervalMs: config.event_flush_interval_ms,
      });
      flushWorker.start();
      ctx.logger.info(`TraceShield flush worker started core=${config.core_base_url}`);
    },
    stop(ctx: { logger: { info: (message: string) => void } }) {
      flushWorker?.stop();
      ctx.logger.info("TraceShield flush worker stopped");
    },
  });
}
