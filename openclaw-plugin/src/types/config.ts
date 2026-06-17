/**
 * TraceShield OpenClaw 插件配置。
 */
export interface PluginConfig {
  /** 插件 ID，默认 traceshield-security-plugin。 */
  plugin_id: string;
  /** 可选网关 ID，用于多实例环境中区分来源。 */
  gateway_id?: string;
  /** Core 或 Mock Core 的 HTTP 地址。 */
  core_base_url: string;
  /** before_tool_call 同步审计超时时间，单位毫秒。 */
  audit_timeout_ms: number;
  /** 异步事件批量上报超时时间，单位毫秒。 */
  event_flush_timeout_ms: number;
  /** 异步事件批量上报间隔，单位毫秒。 */
  event_flush_interval_ms: number;
  /** 运行模式：开发、演示或生产。 */
  mode: "development" | "demo" | "production";
  /** Core 不可用时是否启用本地保守降级策略。 */
  fallback_enabled: boolean;
  /** 是否允许上传完整载荷；默认必须为 false，仅用于本地调试。 */
  debug_full_payload: boolean;
  /** 本地磁盘队列目录，用于 Core 不可用时缓存异步事件。 */
  disk_queue_dir: string;
  /** 内存队列最大事件数，超过后应触发落盘或丢弃低价值事件。 */
  memory_queue_max_events: number;
  /** 允许直接放行的只读工具类别，用于 Core 故障时的本地缓存策略。 */
  local_allow_tool_kinds: string[];
  /** 需要 fail-closed 的高风险工具类别。 */
  high_risk_tool_kinds: string[];
}

/**
 * 插件默认配置，后续实现中可由环境变量或 OpenClaw 配置覆盖。
 */
export const defaultPluginConfig: PluginConfig = {
  plugin_id: "traceshield-security-plugin",
  core_base_url: "http://127.0.0.1:8787",
  audit_timeout_ms: 400,
  event_flush_timeout_ms: 1000,
  event_flush_interval_ms: 2000,
  mode: "development",
  fallback_enabled: true,
  debug_full_payload: false,
  disk_queue_dir: ".traceshield/events",
  memory_queue_max_events: 1000,
  local_allow_tool_kinds: ["file_read"],
  high_risk_tool_kinds: [
    "shell_exec",
    "file_write",
    "file_delete",
    "network_request",
    "message_send",
    "plugin_install",
    "state_change",
  ],
};
