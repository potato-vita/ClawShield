export type LogLevel = "debug" | "info" | "warn" | "error";

export interface Logger {
  debug(message: string, meta?: Record<string, unknown>): void;
  info(message: string, meta?: Record<string, unknown>): void;
  warn(message: string, meta?: Record<string, unknown>): void;
  error(message: string, meta?: Record<string, unknown>): void;
}

const levelOrder: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

export function createLogger(
  namespace = "traceshield",
  minimumLevel: LogLevel = "info",
): Logger {
  const shouldLog = (level: LogLevel): boolean =>
    levelOrder[level] >= levelOrder[minimumLevel];

  const write = (
    level: LogLevel,
    message: string,
    meta?: Record<string, unknown>,
  ): void => {
    if (!shouldLog(level)) {
      return;
    }

    const entry = {
      timestamp: new Date().toISOString(),
      level,
      namespace,
      message,
      ...(meta ? { meta } : {}),
    };

    const line = JSON.stringify(entry);
    if (level === "error") {
      console.error(line);
      return;
    }

    if (level === "warn") {
      console.warn(line);
      return;
    }

    console.log(line);
  };

  return {
    debug: (message, meta) => write("debug", message, meta),
    info: (message, meta) => write("info", message, meta),
    warn: (message, meta) => write("warn", message, meta),
    error: (message, meta) => write("error", message, meta),
  };
}
