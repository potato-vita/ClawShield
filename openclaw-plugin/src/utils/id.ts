export function createId(prefix: string): string {
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}_${Date.now().toString(36)}_${random}`;
}

export function stableHashInput(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, Object.keys(value as Record<string, unknown>).sort());
}
