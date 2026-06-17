export function previewText(value: unknown, maxLength = 500): string {
  const serialized = typeof value === "string" ? value : JSON.stringify(value);
  const text = serialized ?? "";
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength)}...[TRUNCATED:${text.length - maxLength}]`;
}

export function summarizeValue(value: unknown): Record<string, unknown> {
  if (typeof value === "string") {
    return {
      type: "string",
      length: value.length,
      preview: previewText(value),
    };
  }

  if (Array.isArray(value)) {
    return {
      type: "array",
      length: value.length,
      preview: previewText(value),
    };
  }

  if (value !== null && typeof value === "object") {
    return {
      type: "object",
      keys: Object.keys(value as Record<string, unknown>).slice(0, 50),
    };
  }

  return {
    type: typeof value,
    value,
  };
}
