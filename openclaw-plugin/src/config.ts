import { defaultPluginConfig, type PluginConfig } from "./types/config.js";

export interface ConfigSource {
  get?(key: string): unknown;
  [key: string]: unknown;
}

export function loadConfig(source: ConfigSource = {}): PluginConfig {
  const gatewayId = readString(source, "gateway_id", "TRACESHIELD_GATEWAY_ID");
  const mode = readMode(source) ?? defaultPluginConfig.mode;
  const config: PluginConfig = {
    ...defaultPluginConfig,
    plugin_id:
      readString(source, "plugin_id", "TRACESHIELD_PLUGIN_ID") ?? defaultPluginConfig.plugin_id,
    core_base_url:
      readString(source, "core_base_url", "TRACESHIELD_CORE_BASE_URL") ??
      defaultPluginConfig.core_base_url,
    audit_timeout_ms:
      readNumber(source, "audit_timeout_ms", "TRACESHIELD_AUDIT_TIMEOUT_MS") ??
      defaultPluginConfig.audit_timeout_ms,
    event_flush_timeout_ms:
      readNumber(source, "event_flush_timeout_ms", "TRACESHIELD_EVENT_FLUSH_TIMEOUT_MS") ??
      defaultPluginConfig.event_flush_timeout_ms,
    event_flush_interval_ms:
      readNumber(source, "event_flush_interval_ms", "TRACESHIELD_EVENT_FLUSH_INTERVAL_MS") ??
      defaultPluginConfig.event_flush_interval_ms,
    mode,
    fallback_enabled:
      readBoolean(source, "fallback_enabled", "TRACESHIELD_FALLBACK_ENABLED") ??
      defaultPluginConfig.fallback_enabled,
    debug_full_payload:
      readBoolean(source, "debug_full_payload", "TRACESHIELD_DEBUG_FULL_PAYLOAD") ??
      (mode === "production" ? false : defaultPluginConfig.debug_full_payload),
    disk_queue_dir:
      readString(source, "disk_queue_dir", "TRACESHIELD_DISK_QUEUE_DIR") ??
      defaultPluginConfig.disk_queue_dir,
    memory_queue_max_events:
      readNumber(source, "memory_queue_max_events", "TRACESHIELD_MEMORY_QUEUE_MAX_EVENTS") ??
      defaultPluginConfig.memory_queue_max_events,
    local_allow_tool_kinds:
      readStringList(source, "local_allow_tool_kinds", "TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS") ??
      defaultPluginConfig.local_allow_tool_kinds,
    high_risk_tool_kinds:
      readStringList(source, "high_risk_tool_kinds", "TRACESHIELD_HIGH_RISK_TOOL_KINDS") ??
      defaultPluginConfig.high_risk_tool_kinds,
  };

  if (gatewayId !== undefined) {
    config.gateway_id = gatewayId;
  }

  return config;
}

function readEnv(envName: string): string | undefined {
  return globalThis.process?.env?.[envName];
}

function readValue(source: ConfigSource, key: string, envName: string): unknown {
  const fromGetter = source.get?.(key);
  if (fromGetter !== undefined) {
    return fromGetter;
  }

  if (source[key] !== undefined) {
    return source[key];
  }

  return readEnv(envName);
}

function readString(source: ConfigSource, key: string, envName: string): string | undefined {
  const value = readValue(source, key, envName);
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function readNumber(source: ConfigSource, key: string, envName: string): number | undefined {
  const value = readValue(source, key, envName);
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return undefined;
}

function readBoolean(source: ConfigSource, key: string, envName: string): boolean | undefined {
  const value = readValue(source, key, envName);
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    if (value === "true") {
      return true;
    }

    if (value === "false") {
      return false;
    }
  }

  return undefined;
}

function readStringList(source: ConfigSource, key: string, envName: string): string[] | undefined {
  const value = readValue(source, key, envName);
  const items = Array.isArray(value)
    ? value
    : typeof value === "string"
      ? value.split(",")
      : undefined;

  if (!items) {
    return undefined;
  }

  const result = items
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);

  return result.length > 0 ? result : undefined;
}

function readMode(source: ConfigSource): PluginConfig["mode"] | undefined {
  const value = readString(source, "mode", "TRACESHIELD_MODE");
  if (value === "development" || value === "demo" || value === "production") {
    return value;
  }

  return undefined;
}
