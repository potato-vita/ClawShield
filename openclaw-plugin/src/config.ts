import {
  defaultPluginConfig,
  type PluginConfig,
} from "./types/config.js";

declare const process:
  | {
      env?: Record<string, string | undefined>;
    }
  | undefined;

export interface ConfigSource {
  get?(key: string): unknown;
  [key: string]: unknown;
}

const env = process?.env ?? {};

export function loadConfig(source: ConfigSource = {}): PluginConfig {
  const gatewayId = readString(source, "gateway_id", "TRACESHIELD_GATEWAY_ID");
  const config: PluginConfig = {
    ...defaultPluginConfig,
    plugin_id: readString(source, "plugin_id", "TRACESHIELD_PLUGIN_ID")
      ?? defaultPluginConfig.plugin_id,
    core_base_url: readString(source, "core_base_url", "TRACESHIELD_CORE_BASE_URL")
      ?? defaultPluginConfig.core_base_url,
    audit_timeout_ms: readNumber(
      source,
      "audit_timeout_ms",
      "TRACESHIELD_AUDIT_TIMEOUT_MS",
    ) ?? defaultPluginConfig.audit_timeout_ms,
    mode: readMode(source) ?? defaultPluginConfig.mode,
    fallback_enabled: readBoolean(
      source,
      "fallback_enabled",
      "TRACESHIELD_FALLBACK_ENABLED",
    ) ?? defaultPluginConfig.fallback_enabled,
    debug_full_payload: readBoolean(
      source,
      "debug_full_payload",
      "TRACESHIELD_DEBUG_FULL_PAYLOAD",
    ) ?? defaultPluginConfig.debug_full_payload,
  };

  if (gatewayId !== undefined) {
    config.gateway_id = gatewayId;
  }

  return config;
}

function readValue(
  source: ConfigSource,
  key: string,
  envName: string,
): unknown {
  const fromGetter = source.get?.(key);
  if (fromGetter !== undefined) {
    return fromGetter;
  }

  if (source[key] !== undefined) {
    return source[key];
  }

  return env[envName];
}

function readString(
  source: ConfigSource,
  key: string,
  envName: string,
): string | undefined {
  const value = readValue(source, key, envName);
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function readNumber(
  source: ConfigSource,
  key: string,
  envName: string,
): number | undefined {
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

function readBoolean(
  source: ConfigSource,
  key: string,
  envName: string,
): boolean | undefined {
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

function readMode(source: ConfigSource): PluginConfig["mode"] | undefined {
  const value = readString(source, "mode", "TRACESHIELD_MODE");
  if (
    value === "development"
    || value === "demo"
    || value === "production"
  ) {
    return value;
  }

  return undefined;
}
