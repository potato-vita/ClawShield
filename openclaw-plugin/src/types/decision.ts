/**
 * Core 返回给 TraceShield 插件的同步审计决策。
 */
export interface AuditDecision {
  /** 审计动作：放行、告警放行、请求人工确认或阻断。 */
  decision: "ALLOW" | "WARN" | "ASK" | "BLOCK";
  /** 风险等级，用于日志、展示和本地降级参考。 */
  risk_level: "low" | "medium" | "high" | "critical";
  /** 给插件和用户展示的简短原因，不应包含敏感原文。 */
  reason: string;
  /** 命中的策略规则 ID 列表，用于审计和排查。 */
  matched_rules: string[];
  /** Core 策略版本，可选，用于追踪决策来源。 */
  policy_version?: string;
  /** Core 侧证据引用 ID，可选，插件只保存引用而不保存完整证据。 */
  evidence_refs?: string[];
  /** 修改后的工具参数；存在时插件应按 OpenClaw 能力尝试替换参数后放行。 */
  modified_params?: Record<string, unknown> | null;
  /** ASK 决策对应的审批信息；非 ASK 时通常为 null。 */
  approval?: AuditApproval | null;
  /** 是否使用了插件本地降级策略，而不是 Core 正常策略。 */
  fallback_used?: boolean;
}

/**
 * ASK 决策时需要展示给人工确认流程的信息。
 */
export interface AuditApproval {
  /** 审批请求 ID，用于后续关联人工选择结果。 */
  approval_id: string;
  /** 审批标题，应该简洁描述风险动作。 */
  title: string;
  /** 审批描述，说明风险原因和可能影响。 */
  description: string;
  /** 超时后的默认动作。 */
  default_action: "ALLOW" | "BLOCK";
  /** 审批等待超时时间，单位毫秒。 */
  timeout_ms: number;
}
