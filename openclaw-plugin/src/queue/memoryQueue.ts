export interface QueueItem<T> {
  id: string;
  value: T;
  attempts: number;
  enqueued_at: number;
}

export class MemoryQueue<T extends { event_id: string }> {
  private readonly items: QueueItem<T>[] = [];
  private readonly seen = new Set<string>();

  constructor(
    private readonly maxEvents = 1000,
    private readonly maxAttempts = 10,
  ) {}

  enqueue(value: T): boolean {
    if (this.seen.has(value.event_id)) {
      return false;
    }

    this.items.push({
      id: value.event_id,
      value,
      attempts: 0,
      enqueued_at: Date.now(),
    });
    this.seen.add(value.event_id);

    while (this.items.length > this.maxEvents) {
      const removed = this.items.shift();
      if (removed) {
        this.seen.delete(removed.id);
      }
    }

    return true;
  }

  dequeueBatch(limit: number): QueueItem<T>[] {
    const batch = this.items.splice(0, limit);
    for (const item of batch) {
      this.seen.delete(item.id);
    }

    return batch;
  }

  requeue(items: QueueItem<T>[]): void {
    for (const item of items) {
      item.attempts += 1;
      // 超过最大重试次数则丢弃，避免"有毒"事件无限循环
      if (item.attempts > this.maxAttempts) {
        continue;
      }
      if (!this.seen.has(item.id)) {
        this.items.push(item);
        this.seen.add(item.id);
      }
    }
  }

  size(): number {
    return this.items.length;
  }

  drain(): QueueItem<T>[] {
    return this.dequeueBatch(this.items.length);
  }
}
