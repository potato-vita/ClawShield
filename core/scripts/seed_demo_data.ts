import { randomUUID } from "node:crypto";

const baseUrl = process.env.TRACESHIELD_CORE_BASE_URL ?? "http://127.0.0.1:8787";
const seedId = randomUUID();
const sessionId = `demo-session-${seedId}`;
const runId = `demo-run-${seedId}`;
const traceId = `demo-trace-${seedId}`;

interface DemoScenario {
  name: string;
  tool_name: string;
  tool_kind: string;
  raw_params: Record<string, unknown>;
  resource_hint: string;
  risk_hint?: string;
  expected: "ALLOW" | "WARN" | "ASK" | "BLOCK";
}

const scenarios: DemoScenario[] = [
  {
    name: "normal-read",
    tool_name: "file_read",
    tool_kind: "file_read",
    raw_params: { path: "README.md" },
    resource_hint: "README.md",
    expected: "ALLOW",
  },
  {
    name: "secret-read",
    tool_name: "file_read",
    tool_kind: "file_read",
    raw_params: { path: ".env" },
    resource_hint: ".env",
    expected: "BLOCK",
  },
  {
    name: "external-network",
    tool_name: "http_request",
    tool_kind: "network_request",
    raw_params: { url: "https://example.com" },
    resource_hint: "https://example.com",
    risk_hint: "network_request",
    expected: "ASK",
  },
  {
    name: "unknown-tool",
    tool_name: "unknown",
    tool_kind: "unknown",
    raw_params: {},
    resource_hint: "unknown",
    risk_hint: "unknown",
    expected: "WARN",
  },
];

const toolIds: string[] = [];
for (const scenario of scenarios) {
  const toolCallId = `demo-tool-${scenario.name}-${seedId}`;
  toolIds.push(toolCallId);
  const decision = await requestJson<{ decision: string }>("/v1/audit/tool-call", {
    method: "POST",
    body: {
      request_id: `demo-audit-${scenario.name}-${seedId}`,
      schema_version: "v1",
      session_id: sessionId,
      run_id: runId,
      trace_id: traceId,
      tool_call_id: toolCallId,
      tool_name: scenario.tool_name,
      tool_kind: scenario.tool_kind,
      raw_params: scenario.raw_params,
      param_summary: {},
      resource_hint: scenario.resource_hint,
      ...(scenario.risk_hint ? { risk_hint: scenario.risk_hint } : {}),
      context: { user_goal: "Generate safe TraceShield demo data" },
    },
  });
  assert(decision.decision === scenario.expected, `${scenario.name} expected ${scenario.expected}`);
}

const now = Date.now();
const eventResult = await requestJson<{ inserted: number }>("/v1/events/batch", {
  method: "POST",
  body: {
    events: [
      {
        event_id: `demo-message-event-${seedId}`,
        schema_version: "v1",
        type: "message_received",
        timestamp: now,
        plugin_id: "traceshield-demo-seed",
        session_id: sessionId,
        run_id: runId,
        trace_id: traceId,
        mode: "async",
        payload: {
          message_id: `demo-message-${seedId}`,
          role: "user",
          content: "Show the TraceShield runtime audit flow.",
          content_hash: `demo-hash-${seedId}`,
          summary: { type: "string", purpose: "demo" },
        },
      },
      {
        event_id: `demo-result-event-${seedId}`,
        schema_version: "v1",
        type: "after_tool_call",
        timestamp: now + 1,
        plugin_id: "traceshield-demo-seed",
        session_id: sessionId,
        run_id: runId,
        trace_id: traceId,
        mode: "async",
        payload: {
          tool_call_id: toolIds[0],
          tool_name: "file_read",
          tool_kind: "file_read",
          result_preview: "README content was read safely.",
          result_hash: `demo-result-hash-${seedId}`,
          result_summary: { type: "string", purpose: "demo" },
          duration_ms: 8,
        },
      },
    ],
  },
});
assert(eventResult.inserted === 2, "Expected two demo events to be inserted");

console.log("TraceShield demo data created.");
console.log(`run_id=${runId}`);
console.log(`tool_call_ids=${toolIds.join(",")}`);

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(new URL(path, baseUrl), {
    method: options.method ?? "GET",
    ...(options.body !== undefined
      ? { headers: { "content-type": "application/json" }, body: JSON.stringify(options.body) }
      : {}),
  });
  const body = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(`${options.method ?? "GET"} ${path} failed: ${response.status} ${JSON.stringify(body)}`);
  }
  return body as T;
}

function assert(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}
