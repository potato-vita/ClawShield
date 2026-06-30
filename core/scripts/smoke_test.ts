import { randomUUID } from "node:crypto";

const baseUrl = process.env.TRACESHIELD_CORE_BASE_URL ?? "http://127.0.0.1:8787";
const smokeId = randomUUID();
const sessionId = `smoke-session-${smokeId}`;
const runId = `smoke-run-${smokeId}`;
const traceId = `smoke-trace-${smokeId}`;
const toolIds = {
  allow: `smoke-tool-allow-${smokeId}`,
  secret: `smoke-tool-secret-${smokeId}`,
  shell: `smoke-tool-shell-${smokeId}`,
  network: `smoke-tool-network-${smokeId}`,
};
let passed = 0;

await check("health", async () => {
  const health = await get<{ ok: boolean; db_connected: boolean }>("/health");
  assert(health.ok && health.db_connected, "Core or database is not healthy");
});

await check("normal file_read -> ALLOW", async () => {
  const decision = await audit("allow", toolIds.allow, "file_read", "file_read", { path: "README.md" }, "README.md");
  assert(decision.decision === "ALLOW", `Expected ALLOW, got ${decision.decision}`);
});

await check("secret file_read -> BLOCK", async () => {
  const decision = await audit("secret", toolIds.secret, "file_read", "file_read", { path: ".env" }, ".env");
  assert(decision.decision === "BLOCK", `Expected BLOCK, got ${decision.decision}`);
});

await check("rm -rf shell_exec -> ASK", async () => {
  const decision = await audit(
    "shell",
    toolIds.shell,
    "shell",
    "shell_exec",
    { cmd: "rm -rf /tmp/traceshield-smoke" },
    "rm -rf /tmp/traceshield-smoke",
    "file_delete",
  );
  assert(decision.decision === "ASK", `Expected ASK, got ${decision.decision}`);
});

await check("external network_request -> ASK", async () => {
  const decision = await audit(
    "network",
    toolIds.network,
    "http_request",
    "network_request",
    { url: "https://example.com" },
    "https://example.com",
    "network_request",
  );
  assert(decision.decision === "ASK", `Expected ASK, got ${decision.decision}`);
});

await check("message_received extraction", async () => {
  const result = await post<{ inserted: number; message_extracted: number }>("/v1/events/batch", {
    events: [event("message_received", `smoke-message-event-${smokeId}`, {
      message_id: `smoke-message-${smokeId}`,
      role: "user",
      content: "sanitized smoke message",
      content_hash: `smoke-content-hash-${smokeId}`,
      summary: { type: "string", length: 23 },
    })],
  });
  assert(result.inserted === 1 && result.message_extracted === 1, "Message event was not extracted");
});

await check("after_tool_call extraction", async () => {
  const result = await post<{ inserted: number; tool_result_extracted: number }>("/v1/events/batch", {
    events: [event("after_tool_call", `smoke-result-event-${smokeId}`, {
      tool_call_id: toolIds.allow,
      tool_name: "file_read",
      tool_kind: "file_read",
      result_preview: "README smoke result",
      result_hash: `smoke-result-hash-${smokeId}`,
      result_summary: { type: "string", length: 19 },
      duration_ms: 4,
    })],
  });
  assert(result.inserted === 1 && result.tool_result_extracted === 1, "Tool result was not extracted");
});

await check("dashboard runtime status", async () => {
  const status = await get<{ tool_calls_24h: number; policy_hits_24h: number }>("/v1/dashboard/runtime-status");
  assert(status.tool_calls_24h >= 4 && status.policy_hits_24h >= 4, "Dashboard totals are too small");
});

await check("audit timeline", async () => {
  const timeline = await get<{ events: Array<{ run_id: string }> }>("/v1/audit/events?limit=200");
  assert(timeline.events.some((item) => item.run_id === runId), "Smoke run is missing from timeline");
});

await check("risk graph", async () => {
  const graph = await get<{ nodes: unknown[]; edges: unknown[] }>(`/v1/runs/${runId}/risk-graph`);
  assert(graph.nodes.length === 5 && graph.edges.length === 4, "Risk graph shape is invalid");
});

await check("evidence path", async () => {
  const evidence = await get<{ steps: unknown[] }>(`/v1/runs/${runId}/evidence-path`);
  assert(evidence.steps.length === 12, `Expected 12 evidence steps, got ${evidence.steps.length}`);
});

await check("decision detail", async () => {
  const detail = await get<{ decision: { decision: string }; rule_hits: unknown[] }>(
    `/v1/tool-calls/${toolIds.secret}/decision`,
  );
  assert(detail.decision.decision === "BLOCK" && detail.rule_hits.length >= 1, "Decision detail is incomplete");
});

console.log(`TraceShield smoke test passed: ${passed}/12 checks.`);
console.log(`run_id=${runId}`);

async function audit(
  name: string,
  toolCallId: string,
  toolName: string,
  toolKind: string,
  rawParams: Record<string, unknown>,
  resourceHint: string,
  riskHint?: string,
): Promise<{ decision: string }> {
  return post("/v1/audit/tool-call", {
    request_id: `smoke-audit-${name}-${smokeId}`,
    schema_version: "v1",
    session_id: sessionId,
    run_id: runId,
    trace_id: traceId,
    tool_call_id: toolCallId,
    tool_name: toolName,
    tool_kind: toolKind,
    raw_params: rawParams,
    param_summary: {},
    resource_hint: resourceHint,
    ...(riskHint ? { risk_hint: riskHint } : {}),
    context: { user_goal: "Run the TraceShield smoke test" },
  });
}

function event(type: string, eventId: string, payload: Record<string, unknown>): Record<string, unknown> {
  return {
    event_id: eventId,
    schema_version: "v1",
    type,
    timestamp: Date.now(),
    plugin_id: "traceshield-smoke-test",
    session_id: sessionId,
    run_id: runId,
    trace_id: traceId,
    mode: "async",
    payload,
  };
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

async function check(name: string, action: () => Promise<void>): Promise<void> {
  await action();
  passed += 1;
  console.log(`ok ${passed} - ${name}`);
}

function assert(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}
