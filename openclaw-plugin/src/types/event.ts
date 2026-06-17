/**
 * TraceShield 插件上报给 Core 的标准事件。
 * 用于异步记录消息、模型输入输出、工具调用、工具结果和降级决策。
 */
export interface TraceEvent {
  /** 事件唯一 ID，用于 Core 侧幂等去重。 */
  event_id: string;
  /** 事件结构版本，所有事件必须携带，便于后续兼容升级。 */
  schema_version: "v1";
  /** 事件类型，表示当前事件来自哪个运行阶段。 */
  type: TraceEventType;
  /** 事件产生时间，Unix 毫秒时间戳。 */
  timestamp: number;
  /** 插件 ID，用于区分不同 TraceShield 插件实例。 */
  plugin_id: string;
  /** 网关或宿主实例 ID，可选，用于多实例部署时定位来源。 */
  gateway_id?: string;
  /** OpenClaw 会话 ID，用于串联同一用户会话内的事件。 */
  session_id: string;
  /** 单次 Agent 运行 ID，用于区分同一会话中的多轮任务执行。 */
  run_id: string;
  /** Trace 链路 ID，用于串联消息、工具调用和审计决策。 */
  trace_id: string;
  /** 上报模式：同步事件用于阻断链路，异步事件用于审计留痕。 */
  mode: "sync" | "async";
  /** 事件业务载荷，必须先经过摘要、脱敏或哈希处理后再写入。 */
  payload: Record<string, unknown>;
}

/**
 * TraceShield 插件支持的事件类型。
 */
export type TraceEventType =
  | "message_received"
  | "llm_input"
  | "llm_output"
  | "message_sending"
  | "before_tool_call"
  | "after_tool_call"
  | "agent_end"
  | "fallback_decision";

/**
 * before_tool_call 阶段同步发送给 Core 的审计请求。
 * Core 根据该对象返回 ALLOW / WARN / ASK / BLOCK 决策。
 */
export interface AuditRequest {
  /** 请求唯一 ID，用于同步审计请求的幂等和日志关联。 */
  request_id: string;
  /** 请求结构版本，当前固定为 v1。 */
  schema_version: "v1";
  /** OpenClaw 会话 ID。 */
  session_id: string;
  /** 单次 Agent 运行 ID。 */
  run_id: string;
  /** Trace 链路 ID。 */
  trace_id: string;
  /** OpenClaw 工具调用 ID。 */
  tool_call_id: string;
  /** 工具名称，例如 shell、file_read、http_request。 */
  tool_name: string;
  /** 工具类别，用于粗粒度风险识别，例如 shell_exec、file_read。 */
  tool_kind: string;
  /** 原始工具参数，仅限同步审计使用，日志和异步事件不得直接保存完整原文。 */
  raw_params: Record<string, unknown>;
  /** 参数摘要，用于 Core 快速判断资源、动作和风险。 */
  param_summary: Record<string, unknown>;
  /** 资源提示，例如文件路径、URL、命令目标或外部服务名。 */
  resource_hint?: string;
  /** 本地初筛风险提示，例如 file_delete、network_request、unknown。 */
  risk_hint?: string;
  /** 当前工具调用所需的上下文信息。 */
  context: AuditRequestContext;
}

/**
 * 审计请求上下文。
 */
export interface AuditRequestContext {
  /** 用户当前任务目标，可为空，必须避免包含完整敏感原文。 */
  user_goal?: string;
  /** 最近消息的哈希列表，用于关联上下文且避免上传原文。 */
  recent_message_hashes?: string[];
  /** 当前工作区根目录，用于判断文件访问边界。 */
  workspace_root?: string;
}
