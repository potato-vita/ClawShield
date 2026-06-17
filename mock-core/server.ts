import { createServer, type ServerResponse } from "node:http";

interface AuditRequest {
  tool_name?: string;
  tool_kind?: string;
  raw_params?: Record<string, unknown>;
  resource_hint?: string;
  risk_hint?: string;
}

const allowedHosts = new Set(["localhost", "127.0.0.1"]);
const port = Number(process.env.MOCK_CORE_PORT ?? 8787);

const server = createServer(async (request, response) => {
  if (request.method === "POST" && request.url === "/v1/audit/tool-call") {
    const body = await readJson(request);
    sendJson(response, 200, decide(body as AuditRequest));
    return;
  }

  if (request.method === "POST" && request.url === "/v1/events/batch") {
    sendJson(response, 200, { ok: true });
    return;
  }

  sendJson(response, 404, { error: "not_found" });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`TraceShield mock-core listening on http://127.0.0.1:${port}`);
});

function decide(request: AuditRequest): Record<string, unknown> {
  const haystack = JSON.stringify({
    tool_name: request.tool_name,
    tool_kind: request.tool_kind,
    raw_params: request.raw_params,
    resource_hint: request.resource_hint,
    risk_hint: request.risk_hint,
  }).toLowerCase();

  if (/\brm\s+-rf\b/.test(haystack)) {
    return block("critical", "Dangerous recursive deletion command.", ["dangerous_rm_rf"]);
  }

  if (haystack.includes(".env") || haystack.includes("id_rsa") || haystack.includes("private key")) {
    return block("critical", "Sensitive file or secret access is blocked.", ["secret_file_access"]);
  }

  if (request.risk_hint === "network_request" || request.tool_kind === "network_request") {
    const url = extractUrl(request);
    if (url && !allowedHosts.has(url.hostname)) {
      return {
        decision: "ASK",
        risk_level: "medium",
        reason: "External network request requires approval.",
        matched_rules: ["external_url_requires_approval"],
        modified_params: null,
        approval: {
          approval_id: `appr_${Date.now()}`,
          title: "External network request",
          description: `Allow request to ${url.hostname}?`,
          default_action: "BLOCK",
          timeout_ms: 30000,
        },
      };
    }
  }

  if (request.tool_kind === "file_read" || request.risk_hint === "file_read") {
    return {
      decision: "ALLOW",
      risk_level: "low",
      reason: "Ordinary read-only operation.",
      matched_rules: ["readonly_allow"],
      modified_params: null,
      approval: null,
    };
  }

  return {
    decision: "WARN",
    risk_level: "medium",
    reason: "Operation is allowed with warning by mock policy.",
    matched_rules: ["mock_warn_default"],
    modified_params: null,
    approval: null,
  };
}

function block(riskLevel: string, reason: string, matchedRules: string[]): Record<string, unknown> {
  return {
    decision: "BLOCK",
    risk_level: riskLevel,
    reason,
    matched_rules: matchedRules,
    modified_params: null,
    approval: null,
  };
}

function extractUrl(request: AuditRequest): URL | undefined {
  const text = `${request.resource_hint ?? ""} ${JSON.stringify(request.raw_params ?? {})}`;
  const match = text.match(/https?:\/\/[^\s"'{}]+/);
  if (!match) {
    return undefined;
  }

  try {
    return new URL(match[0]);
  } catch {
    return undefined;
  }
}

async function readJson(request: NodeJS.ReadableStream): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  const text = Buffer.concat(chunks).toString("utf8");
  return text.length > 0 ? JSON.parse(text) : {};
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}
