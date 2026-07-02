import type { EvidenceStep } from "@/types/evidence";
import type { GraphEdge, GraphNode } from "@/types/graph";
import type { Policy } from "@/types/policy";
import type { AuditRun, AuditSession, ConversationMessage, DashboardMetrics, RuntimeStatus, TimelineEvent } from "@/types/session";
import type { ToolCall } from "@/types/toolCall";

export const mockSessions: AuditSession[] = [
  { id: "payroll-leak-demo", title: "Payroll exfiltration", subtitle: "read_file → external_send", risk: "critical", time: "now", runIds: ["run-payroll-001"], unread: true },
  { id: "finance-review", title: "Quarterly finance review", subtitle: "spreadsheet analysis", risk: "medium", time: "4m", runIds: ["run-finance-024"] },
  { id: "docs-refactor", title: "Documentation refactor", subtitle: "read → edit → build", risk: "low", time: "18m", runIds: ["run-docs-116"] },
];

export const mockRuns: AuditRun[] = [
  { id: "run-payroll-001", sessionId: "payroll-leak-demo", title: "Payroll leak attempt", startedAt: "2026-07-01T16:48:21+08:00", decision: "block", risk: "critical", summary: "Sensitive payroll data was processed and targeted at an untrusted external domain." },
  { id: "run-finance-024", sessionId: "finance-review", title: "Finance workbook review", startedAt: "2026-07-01T16:44:02+08:00", decision: "review", risk: "medium", summary: "An internal finance workbook was read for variance analysis." },
  { id: "run-docs-116", sessionId: "docs-refactor", title: "Documentation cleanup", startedAt: "2026-07-01T16:30:18+08:00", decision: "allow", risk: "low", summary: "Repository documentation was reformatted and validated." },
];

export const mockGraphNodes: GraphNode[] = [
  { id: "intent", type: "user_intent", label: "User Request", detail: "Analyze the payroll workbook and deliver a concise variance report.", risk: "low", evidenceStepId: "evidence-01" },
  { id: "shell", type: "tool_call", label: "shell_exec", detail: "Locate payroll inputs in the workspace", risk: "medium", toolCallId: "tc-shell", evidenceStepId: "evidence-02" },
  { id: "read", type: "sensitive_object", label: "read_file", detail: "payroll.xlsx · confidential", risk: "high", toolCallId: "tc-read", evidenceStepId: "evidence-03" },
  { id: "object", type: "sensitive_object", label: "Sensitive Object", detail: "payroll.xlsx", risk: "high", evidenceStepId: "evidence-03", lane: "evidence" },
  { id: "process", type: "tool_call", label: "process_data", detail: "Aggregate salaries and employee identifiers", risk: "high", toolCallId: "tc-process", evidenceStepId: "evidence-04" },
  { id: "send", type: "network_sink", label: "external_send", detail: "suspicious-exfil.com", risk: "critical", decision: "block", toolCallId: "tc-send", evidenceStepId: "evidence-05" },
  { id: "sink", type: "network_sink", label: "Untrusted Sink", detail: "suspicious-exfil.com", risk: "critical", evidenceStepId: "evidence-05", lane: "evidence" },
  { id: "blocked", type: "blocked", label: "BLOCKED", detail: "deny_sensitive_exfiltration", risk: "critical", decision: "block", policyId: "policy-exfil", evidenceStepId: "evidence-06" },
];

export const mockGraphEdges: GraphEdge[] = [
  { id: "e1", source: "intent", target: "shell", kind: "main" },
  { id: "e2", source: "shell", target: "read", kind: "main" },
  { id: "e3", source: "read", target: "process", kind: "main" },
  { id: "e4", source: "process", target: "send", kind: "main" },
  { id: "e5", source: "send", target: "blocked", label: "pre-execution", kind: "main" },
  { id: "e6", source: "object", target: "read", label: "classified", kind: "evidence" },
  { id: "e7", source: "sink", target: "send", label: "untrusted", kind: "evidence" },
];

export const mockEvidence: EvidenceStep[] = [
  { id: "evidence-01", step: "01", type: "intent", title: "User request normalized", detail: "Payroll variance analysis", status: "observed", nodeId: "intent" },
  { id: "evidence-02", step: "02", type: "tool", title: "Workspace enumerated", detail: "shell_exec · scoped", status: "verified", nodeId: "shell" },
  { id: "evidence-03", step: "03", type: "object", title: "Sensitive file accessed", detail: "payroll.xlsx · confidential", status: "risk", nodeId: "read", fingerprint: "sha256:2f42…a91c" },
  { id: "evidence-04", step: "04", type: "tool", title: "Sensitive fields processed", detail: "salary + employee identifiers", status: "risk", nodeId: "process" },
  { id: "evidence-05", step: "05", type: "network", title: "Trust boundary targeted", detail: "suspicious-exfil.com", status: "critical", nodeId: "send" },
  { id: "evidence-06", step: "06", type: "decision", title: "Execution blocked", detail: "deny_sensitive_exfiltration", status: "blocked", nodeId: "blocked" },
];

export const mockToolCalls: ToolCall[] = [
  { id: "tc-shell", sessionId: "payroll-leak-demo", runId: "run-payroll-001", time: "16:48:21.108", toolName: "shell_exec", toolKind: "shell", resource: "workspace/payroll", decision: "review", riskLevel: "medium", latencyMs: 11, policyHits: ["observe_shell"], argumentsSummary: "List candidate workbook files", nodeId: "shell" },
  { id: "tc-read", sessionId: "payroll-leak-demo", runId: "run-payroll-001", time: "16:48:21.482", toolName: "read_file", toolKind: "filesystem", resource: "payroll.xlsx", decision: "review", riskLevel: "high", latencyMs: 18, policyHits: ["classify_sensitive_file"], argumentsSummary: "Read workbook metadata and relevant cells", nodeId: "read" },
  { id: "tc-process", sessionId: "payroll-leak-demo", runId: "run-payroll-001", time: "16:48:22.031", toolName: "process_data", toolKind: "transform", resource: "in-memory dataset", decision: "review", riskLevel: "high", latencyMs: 24, policyHits: ["track_sensitive_derivative"], argumentsSummary: "Aggregate salary variance by team", nodeId: "process" },
  { id: "tc-send", sessionId: "payroll-leak-demo", runId: "run-payroll-001", time: "16:48:22.417", toolName: "external_send", toolKind: "network", resource: "suspicious-exfil.com", decision: "block", riskLevel: "critical", latencyMs: 7, policyHits: ["deny_sensitive_exfiltration", "untrusted_network_sink"], argumentsSummary: "Send generated report to external destination", nodeId: "send" },
  { id: "tc-finance-read", sessionId: "finance-review", runId: "run-finance-024", time: "16:44:03.102", toolName: "read_file", toolKind: "filesystem", resource: "finance-q2.xlsx", decision: "allow", riskLevel: "medium", latencyMs: 15, policyHits: [], argumentsSummary: "Read quarterly totals", nodeId: "read" },
  { id: "tc-docs", sessionId: "docs-refactor", runId: "run-docs-116", time: "16:30:18.901", toolName: "shell_exec", toolKind: "shell", resource: "docs/", decision: "allow", riskLevel: "low", latencyMs: 9, policyHits: [], argumentsSummary: "Run markdown formatter", nodeId: "shell" },
];

export const mockTimeline: TimelineEvent[] = mockEvidence.map((step, index) => ({
  id: `timeline-${step.id}`,
  runId: "run-payroll-001",
  time: `16:48:${String(21 + Math.floor(index / 2)).padStart(2, "0")}.${String(108 + index * 83).slice(-3)}`,
  title: step.title,
  detail: step.detail,
  risk: step.status === "critical" || step.status === "blocked" ? "critical" : step.status === "risk" ? "high" : "low",
  nodeId: step.nodeId,
}));

export const mockConversation: ConversationMessage[] = [
  { id: "message-1", role: "user", summary: "Requested a payroll variance summary and asked that the result be delivered externally." },
  { id: "message-2", role: "assistant", summary: "Planned to locate the workbook, calculate variance, then deliver the report." },
  { id: "message-3", role: "assistant", summary: "TraceShield stopped the outbound step before the external tool executed." },
];

export const mockPolicies: Policy[] = [
  { id: "policy-exfil", name: "Sensitive data exfiltration guard", ruleId: "deny_sensitive_exfiltration", severity: "critical", action: "BLOCK", enabled: true, hitCount: 19, lastHitTime: "just now", description: "Blocks sensitive derivatives from reaching untrusted destinations." },
  { id: "policy-shell", name: "Dangerous shell command guard", ruleId: "deny_dangerous_shell", severity: "high", action: "BLOCK", enabled: true, hitCount: 7, lastHitTime: "22m ago", description: "Blocks destructive or privilege-escalating shell commands." },
  { id: "policy-network", name: "External request approval", ruleId: "review_external_network", severity: "medium", action: "REVIEW", enabled: true, hitCount: 42, lastHitTime: "4m ago", description: "Requires review before tools contact unknown domains." },
  { id: "policy-unknown", name: "Unknown tool observer", ruleId: "alert_unknown_tool", severity: "low", action: "ALERT", enabled: false, hitCount: 14, lastHitTime: "1h ago", description: "Raises an alert for tools missing from the registry." },
];

export const mockMetrics: DashboardMetrics = { toolCalls24h: 1284, blocked: 19, highRisk: 37, policyHits: 82 };
export const mockRuntimeStatus: RuntimeStatus = { coreOnline: false, databaseConnected: false, pluginLastSeen: "preview data", eventsIngested: 1284, queueSize: 0, coreVersion: "mock", policyVersion: "preview" };
