import { randomUUID } from "node:crypto";

/**
 * 生成带前缀的事件/审计 ID。
 * 使用 crypto.randomUUID() 保证不可预测性，适合安全审计场景。
 */
export function createId(prefix: string): string {
  const uuid = randomUUID();
  return `${prefix}_${Date.now().toString(36)}_${uuid.slice(0, 8)}`;
}

export function stableHashInput(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, Object.keys(value as Record<string, unknown>).sort());
}
