import { afterEach, describe, expect, it } from "vitest";
import { loadConfig } from "../config.js";
import { defaultPluginConfig } from "../types/config.js";

const envNames = [
  "TRACESHIELD_CORE_BASE_URL",
  "TRACESHIELD_AUDIT_TIMEOUT_MS",
  "TRACESHIELD_EVENT_FLUSH_TIMEOUT_MS",
  "TRACESHIELD_EVENT_FLUSH_INTERVAL_MS",
  "TRACESHIELD_DISK_QUEUE_DIR",
  "TRACESHIELD_MEMORY_QUEUE_MAX_EVENTS",
  "TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS",
  "TRACESHIELD_HIGH_RISK_TOOL_KINDS",
  "TRACESHIELD_MODE",
  "TRACESHIELD_DEBUG_FULL_PAYLOAD",
] as const;

describe("loadConfig", () => {
  afterEach(() => {
    for (const name of envNames) {
      delete process.env[name];
    }
  });

  it("loads default config", () => {
    expect(loadConfig()).toEqual(defaultPluginConfig);
  });

  it("uses source values before environment values", () => {
    process.env.TRACESHIELD_CORE_BASE_URL = "http://env.example";

    const config = loadConfig({
      core_base_url: "http://source.example",
      audit_timeout_ms: 123,
      event_flush_timeout_ms: 456,
      event_flush_interval_ms: 789,
      disk_queue_dir: "/tmp/traceshield-events",
      memory_queue_max_events: 321,
    });

    expect(config.core_base_url).toBe("http://source.example");
    expect(config.audit_timeout_ms).toBe(123);
    expect(config.event_flush_timeout_ms).toBe(456);
    expect(config.event_flush_interval_ms).toBe(789);
    expect(config.disk_queue_dir).toBe("/tmp/traceshield-events");
    expect(config.memory_queue_max_events).toBe(321);
  });

  it("reads list values from arrays and comma-separated strings", () => {
    const fromArray = loadConfig({
      local_allow_tool_kinds: ["file_read", "read_only"],
      high_risk_tool_kinds: ["shell_exec", "file_delete"],
    });

    expect(fromArray.local_allow_tool_kinds).toEqual(["file_read", "read_only"]);
    expect(fromArray.high_risk_tool_kinds).toEqual(["shell_exec", "file_delete"]);

    const fromString = loadConfig({
      local_allow_tool_kinds: "file_read, read_only",
      high_risk_tool_kinds: "shell_exec,file_write,file_delete",
    });

    expect(fromString.local_allow_tool_kinds).toEqual(["file_read", "read_only"]);
    expect(fromString.high_risk_tool_kinds).toEqual(["shell_exec", "file_write", "file_delete"]);
  });

  it("uses environment variables when source values are absent", () => {
    process.env.TRACESHIELD_EVENT_FLUSH_TIMEOUT_MS = "1500";
    process.env.TRACESHIELD_EVENT_FLUSH_INTERVAL_MS = "2500";
    process.env.TRACESHIELD_DISK_QUEUE_DIR = "/tmp/env-events";
    process.env.TRACESHIELD_MEMORY_QUEUE_MAX_EVENTS = "42";
    process.env.TRACESHIELD_LOCAL_ALLOW_TOOL_KINDS = "file_read,read_only";
    process.env.TRACESHIELD_HIGH_RISK_TOOL_KINDS = "shell_exec,network_request";

    const config = loadConfig();

    expect(config.event_flush_timeout_ms).toBe(1500);
    expect(config.event_flush_interval_ms).toBe(2500);
    expect(config.disk_queue_dir).toBe("/tmp/env-events");
    expect(config.memory_queue_max_events).toBe(42);
    expect(config.local_allow_tool_kinds).toEqual(["file_read", "read_only"]);
    expect(config.high_risk_tool_kinds).toEqual(["shell_exec", "network_request"]);
  });

  it("falls back for invalid mode, numbers, booleans, and empty lists", () => {
    const config = loadConfig({
      mode: "invalid",
      audit_timeout_ms: "slow",
      event_flush_timeout_ms: Number.NaN,
      event_flush_interval_ms: "",
      memory_queue_max_events: "many",
      fallback_enabled: "yes",
      debug_full_payload: "1",
      local_allow_tool_kinds: "",
      high_risk_tool_kinds: [],
    });

    expect(config.mode).toBe(defaultPluginConfig.mode);
    expect(config.audit_timeout_ms).toBe(defaultPluginConfig.audit_timeout_ms);
    expect(config.event_flush_timeout_ms).toBe(defaultPluginConfig.event_flush_timeout_ms);
    expect(config.event_flush_interval_ms).toBe(defaultPluginConfig.event_flush_interval_ms);
    expect(config.memory_queue_max_events).toBe(defaultPluginConfig.memory_queue_max_events);
    expect(config.fallback_enabled).toBe(defaultPluginConfig.fallback_enabled);
    expect(config.debug_full_payload).toBe(false);
    expect(config.local_allow_tool_kinds).toEqual(defaultPluginConfig.local_allow_tool_kinds);
    expect(config.high_risk_tool_kinds).toEqual(defaultPluginConfig.high_risk_tool_kinds);
  });

  it("keeps debug_full_payload disabled by default in production mode", () => {
    expect(loadConfig({ mode: "production" }).debug_full_payload).toBe(false);
    expect(loadConfig({ mode: "production", debug_full_payload: true }).debug_full_payload).toBe(
      true,
    );
  });
});
