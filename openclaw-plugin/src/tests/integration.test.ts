/**
 * 集成测试：启动 Mock Core，走完整 HTTP 链路验证插件审计决策。
 *
 * 测试流程：
 *   1. 启动 mock-core 在随机端口
 *   2. 用真实的 AuditClient 发送 POST /v1/audit/tool-call
 *   3. 验证 ALLOW / BLOCK / ASK / WARN 四种决策
 *   4. 关闭 mock-core，验证超时 → fallback 链路
 */
import { describe, expect, it, beforeAll, afterAll } from "vitest";
import { createServer } from "node:http";
import type { Server } from "node:http";
import { AuditClient, parseAuditDecision } from "../client/auditClient.js";
import { mapAuditDecision } from "../policy/decisionMapper.js";
import { evaluateFallbackPolicy } from "../policy/fallbackPolicy.js";
import { defaultPluginConfig } from "../types/config.js";
import type { AuditRequest } from "../types/event.js";

const MOCK_DECISIONS = new Map<
  string,
  (body: Record<string, unknown>) => Record<string, unknown>
>();

describe("integration: audit round-trip via real HTTP", () => {
  let server: Server;
  let baseUrl: string;
  let auditClient: AuditClient;

  // ---------- 启动 Mock Core ----------
  beforeAll(async () => {
    server = createServer(async (req, res) => {
      if (req.method === "POST" && req.url === "/v1/audit/tool-call") {
        const body = await readJson(req);
        const handler = MOCK_DECISIONS.get("audit");
        const result = handler
          ? handler(body as Record<string, unknown>)
          : {
              decision: "ALLOW",
              risk_level: "low",
              reason: "default allow",
              matched_rules: ["default"],
            };
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify(result));
        return;
      }

      if (req.method === "POST" && req.url === "/v1/events/batch") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
        return;
      }

      res.writeHead(404, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "not_found" }));
    });

    await new Promise<void>((resolve) => {
      // 端口 0 = 随机端口
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address();
        if (addr && typeof addr === "object") {
          baseUrl = `http://127.0.0.1:${addr.port}`;
        }
        resolve();
      });
    });

    auditClient = new AuditClient({
      baseUrl,
      timeoutMs: 2000,
    });
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  function auditRequest(overrides: Partial<AuditRequest>): AuditRequest {
    return {
      request_id: "test-req-1",
      schema_version: "v1",
      session_id: "test-session",
      run_id: "test-run",
      trace_id: "test-trace",
      tool_call_id: "test-tool-1",
      tool_name: "file_read",
      tool_kind: "file_read",
      raw_params: {},
      param_summary: {},
      context: {},
      ...overrides,
    };
  }

  // ====== 场景 1: ALLOW ======
  it("returns ALLOW for normal file read", async () => {
    MOCK_DECISIONS.set("audit", () => ({
      decision: "ALLOW",
      risk_level: "low",
      reason: "Normal file read.",
      matched_rules: ["readonly_allow"],
    }));

    const decision = await auditClient.auditToolCall(
      auditRequest({ tool_name: "file_read", tool_kind: "file_read", resource_hint: "README.md" }),
    );

    expect(decision.decision).toBe("ALLOW");
    expect(decision.risk_level).toBe("low");

    const result = mapAuditDecision(decision);
    expect(result.block).toBeUndefined();
    expect(result.requireApproval).toBeUndefined();
  });

  // ====== 场景 2: BLOCK ======
  it("returns BLOCK for dangerous command (rm -rf)", async () => {
    MOCK_DECISIONS.set("audit", () => ({
      decision: "BLOCK",
      risk_level: "critical",
      reason: "Dangerous recursive deletion.",
      matched_rules: ["dangerous_rm_rf"],
    }));

    const decision = await auditClient.auditToolCall(
      auditRequest({
        tool_name: "shell",
        tool_kind: "shell_exec",
        raw_params: { cmd: "rm -rf /" },
      }),
    );

    expect(decision.decision).toBe("BLOCK");
    expect(decision.risk_level).toBe("critical");

    const result = mapAuditDecision(decision);
    expect(result.block).toBe(true);
    expect(result.blockReason).toContain("TraceShield BLOCKED");
    expect(result.blockReason).toContain("Dangerous recursive deletion");
  });

  // ====== 场景 3: ASK ======
  it("returns ASK for external URL", async () => {
    MOCK_DECISIONS.set("audit", () => ({
      decision: "ASK",
      risk_level: "medium",
      reason: "External network request requires approval.",
      matched_rules: ["external_url_requires_approval"],
      approval: {
        approval_id: "appr_test",
        title: "External network request",
        description: "Allow request to example.com?",
        default_action: "BLOCK",
        timeout_ms: 30000,
      },
    }));

    const decision = await auditClient.auditToolCall(
      auditRequest({
        tool_name: "http_request",
        tool_kind: "network_request",
        resource_hint: "https://example.com",
      }),
    );

    expect(decision.decision).toBe("ASK");

    const result = mapAuditDecision(decision);
    expect(result.requireApproval).toBeDefined();
    expect(result.requireApproval?.title).toBe("External network request");
    expect(result.requireApproval?.defaultAction).toBe("BLOCK");
  });

  // ====== 场景 4: WARN ======
  it("returns WARN without blocking", async () => {
    MOCK_DECISIONS.set("audit", () => ({
      decision: "WARN",
      risk_level: "medium",
      reason: "Operation allowed with warning.",
      matched_rules: ["mock_warn_default"],
    }));

    const decision = await auditClient.auditToolCall(
      auditRequest({ tool_name: "shell", tool_kind: "shell_exec", raw_params: { cmd: "ls" } }),
    );

    expect(decision.decision).toBe("WARN");

    const result = mapAuditDecision(decision);
    expect(result.warning).toBe("Operation allowed with warning.");
    expect(result.block).toBeUndefined();
  });

  // ====== 场景 5: modified_params ======
  it("maps modified_params to param replacement", async () => {
    MOCK_DECISIONS.set("audit", () => ({
      decision: "ALLOW",
      risk_level: "low",
      reason: "Parameter sanitized.",
      matched_rules: ["sanitized_params"],
      modified_params: { cmd: "ls -la" },
    }));

    const decision = await auditClient.auditToolCall(
      auditRequest({ tool_name: "shell", tool_kind: "shell_exec", raw_params: { cmd: "ls" } }),
    );

    const result = mapAuditDecision(decision);
    expect(result.modifiedParams).toEqual({ cmd: "ls -la" });
  });
});

// ====== 场景 6: Core 不可用 → fallback ======
describe("integration: fallback when Core is unreachable", () => {
  it("blocks high-risk tool when Core is down", () => {
    const request: AuditRequest = {
      request_id: "fb-1",
      schema_version: "v1",
      session_id: "s1",
      run_id: "r1",
      trace_id: "t1",
      tool_call_id: "tc1",
      tool_name: "shell",
      tool_kind: "shell_exec",
      raw_params: { cmd: "rm -rf /tmp" },
      param_summary: {},
      context: {},
    };

    const decision = evaluateFallbackPolicy(request, defaultPluginConfig);
    expect(decision.decision).toBe("BLOCK");
    expect(decision.fallback_used).toBe(true);
  });

  it("blocks sensitive file read via shell_exec in fallback", () => {
    const request: AuditRequest = {
      request_id: "fb-2",
      schema_version: "v1",
      session_id: "s1",
      run_id: "r1",
      trace_id: "t1",
      tool_call_id: "tc2",
      tool_name: "shell",
      tool_kind: "shell_exec",
      raw_params: { cmd: "cat .env" },
      param_summary: {},
      resource_hint: ".env",
      context: {},
    };

    const decision = evaluateFallbackPolicy(request, defaultPluginConfig);
    expect(decision.decision).toBe("BLOCK");
    expect(decision.fallback_used).toBe(true);
  });
});

// ====== 场景 7: HTTP 超时 ======
describe("integration: HTTP timeout triggers fallback", () => {
  it("throws on audit timeout and falls back", async () => {
    // 用一个不存在的地址模拟网络不可达
    const deadClient = new AuditClient({
      baseUrl: "http://127.0.0.1:1", // 几乎不可能有服务
      timeoutMs: 200,
    });

    const request: AuditRequest = {
      request_id: "to-1",
      schema_version: "v1",
      session_id: "s1",
      run_id: "r1",
      trace_id: "t1",
      tool_call_id: "tc1",
      tool_name: "file_read",
      tool_kind: "file_read",
      raw_params: { path: "README.md" },
      param_summary: {},
      resource_hint: "README.md",
      context: {},
    };

    // AuditClient 应该超时抛错
    await expect(deadClient.auditToolCall(request)).rejects.toThrow();

    // fallback 应该能正常执行
    const fallbackDecision = evaluateFallbackPolicy(request, defaultPluginConfig);
    expect(fallbackDecision.fallback_used).toBe(true);
    // 普通只读在无缓存时走 ASK
    expect(["ASK", "ALLOW"]).toContain(fallbackDecision.decision);
  });
});

// ---------- 工具函数 ----------
async function readJson(stream: NodeJS.ReadableStream): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  const text = Buffer.concat(chunks).toString("utf8");
  return text.length > 0 ? JSON.parse(text) : {};
}
