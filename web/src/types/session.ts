export type RiskLevel = "critical" | "high" | "medium" | "low";
export type Decision = "block" | "review" | "allow";

export interface AuditSession {
  id: string;
  title: string;
  subtitle: string;
  risk: RiskLevel;
  time: string;
  runIds: string[];
  unread?: boolean;
}

export interface AuditRun {
  id: string;
  sessionId: string;
  title: string;
  startedAt: string;
  decision: Decision;
  risk: RiskLevel;
  summary: string;
}

export interface TimelineEvent {
  id: string;
  runId: string;
  time: string;
  title: string;
  detail: string;
  risk: RiskLevel;
  nodeId?: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  summary: string;
}

export interface DashboardMetrics {
  toolCalls24h: number;
  blocked: number;
  highRisk: number;
  policyHits: number;
}

export interface RuntimeStatus {
  coreOnline: boolean;
  databaseConnected: boolean;
  pluginLastSeen: string;
  eventsIngested: number;
  queueSize: number;
  coreVersion: string;
  policyVersion: string;
}
