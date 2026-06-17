/**
 * TraceShield OpenClaw 插件演示脚本。
 *
 * 前置条件：先启动 mock-core（cd mock-core && npm run dev）
 * 然后运行：cd openclaw-plugin && npm run demo:openclaw
 *
 * 演示 5 个场景：
 *   1. 正常读取 README → ALLOW
 *   2. 读取 .env → BLOCK
 *   3. 执行 rm -rf → BLOCK
 *   4. 访问外部 URL → ASK
 *   5. Core 关闭后高危命令 → 本地降级 BLOCK
 */
import { AuditClient } from "../client/auditClient.js";
import { mapAuditDecision } from "../policy/decisionMapper.js";
import { evaluateFallbackPolicy } from "../policy/fallbackPolicy.js";
import { loadConfig } from "../config.js";
import { createLogger } from "../logger.js";
import { createId } from "../utils/id.js";
import { defaultPluginConfig } from "../types/config.js";
import type { AuditDecision } from "../types/decision.js";
import type { AuditRequest } from "../types/event.js";

const logger = createLogger("traceshield-demo", "info");

async function main(): Promise<void> {
  const config = loadConfig({});
  const auditClient = new AuditClient({
    baseUrl: config.core_base_url,
    timeoutMs: config.audit_timeout_ms,
  });

  console.log("╔══════════════════════════════════════════╗");
  console.log("║   TraceShield OpenClaw 插件展示面板      ║");
  console.log("╠══════════════════════════════════════════╣");
  console.log(`║ 插件 ID      : ${config.plugin_id.padEnd(26)} ║`);
  console.log(`║ Core 地址    : ${config.core_base_url.padEnd(26)} ║`);
  console.log(`║ 审计超时     : ${String(config.audit_timeout_ms + "ms").padEnd(26)} ║`);
  console.log(`║ 降级策略     : ${(config.fallback_enabled ? "已启用" : "已禁用").padEnd(26)} ║`);
  console.log(`║ 运行模式     : ${config.mode.padEnd(26)} ║`);
  console.log("╚══════════════════════════════════════════╝");
  console.log("");

  let passed = 0;
  let failed = 0;

  // ====== 场景 1: 正常读取 README → ALLOW ======
  console.log("━".repeat(50));
  console.log("场景 1: 正常读取 README → 应返回 ALLOW");
  console.log("━".repeat(50));
  try {
    const result = await auditClient.auditToolCall(
      makeRequest({
        tool_name: "file_read",
        tool_kind: "file_read",
        raw_params: { path: "README.md" },
        resource_hint: "README.md",
      }),
    );
    const mapped = mapAuditDecision(result);
    console.log(`  Core 决策 : ${result.decision} (risk: ${result.risk_level})`);
    console.log(`  原因      : ${result.reason}`);
    console.log(`  命中规则  : ${result.matched_rules.join(", ")}`);
    console.log(
      `  映射结果  : ${mapped.block ? "BLOCK" : mapped.requireApproval ? "ASK" : mapped.warning ? "WARN" : "ALLOW (放行)"}`,
    );

    if (result.decision === "ALLOW") {
      console.log("  ✅ 通过 — 正常只读被放行");
      passed++;
    } else {
      console.log(`  ⚠️  预期 ALLOW，实际 ${result.decision}`);
      failed++;
    }
  } catch (err) {
    console.log(`  ❌ 异常: ${err instanceof Error ? err.message : String(err)}`);
    failed++;
  }

  // ====== 场景 2: 读取 .env → BLOCK ======
  console.log("");
  console.log("━".repeat(50));
  console.log("场景 2: 读取 .env → 应返回 BLOCK");
  console.log("━".repeat(50));
  try {
    const result = await auditClient.auditToolCall(
      makeRequest({
        tool_name: "file_read",
        tool_kind: "file_read",
        raw_params: { path: ".env" },
        resource_hint: ".env",
      }),
    );
    const mapped = mapAuditDecision(result);
    console.log(`  Core 决策 : ${result.decision} (risk: ${result.risk_level})`);
    console.log(`  原因      : ${result.reason}`);
    console.log(`  命中规则  : ${result.matched_rules.join(", ")}`);
    console.log(`  映射结果  : ${mapped.block ? "BLOCK (阻断)" : "NOT BLOCKED"}`);

    if (result.decision === "BLOCK") {
      console.log("  ✅ 通过 — 敏感文件被阻断");
      passed++;
    } else {
      console.log(`  ⚠️  预期 BLOCK，实际 ${result.decision}`);
      failed++;
    }
  } catch (err) {
    console.log(`  ❌ 异常: ${err instanceof Error ? err.message : String(err)}`);
    failed++;
  }

  // ====== 场景 3: rm -rf → BLOCK ======
  console.log("");
  console.log("━".repeat(50));
  console.log("场景 3: 执行 rm -rf → 应返回 BLOCK");
  console.log("━".repeat(50));
  try {
    const result = await auditClient.auditToolCall(
      makeRequest({
        tool_name: "shell",
        tool_kind: "shell_exec",
        raw_params: { cmd: "rm -rf /tmp/traceshield-demo" },
        risk_hint: "file_delete",
      }),
    );
    const mapped = mapAuditDecision(result);
    console.log(`  Core 决策 : ${result.decision} (risk: ${result.risk_level})`);
    console.log(`  原因      : ${result.reason}`);
    console.log(`  命中规则  : ${result.matched_rules.join(", ")}`);
    if (mapped.block) {
      console.log("  ✅ 通过 — 危险命令被阻断");
      passed++;
    } else {
      console.log(`  ⚠️  预期 BLOCK，实际 ${result.decision}`);
      failed++;
    }
  } catch (err) {
    console.log(`  ❌ 异常: ${err instanceof Error ? err.message : String(err)}`);
    failed++;
  }

  // ====== 场景 4: 外部 URL → ASK ======
  console.log("");
  console.log("━".repeat(50));
  console.log("场景 4: 访问外部 URL → 应返回 ASK");
  console.log("━".repeat(50));
  try {
    const result = await auditClient.auditToolCall(
      makeRequest({
        tool_name: "http_request",
        tool_kind: "network_request",
        raw_params: { url: "https://example.com" },
        resource_hint: "https://example.com",
        risk_hint: "network_request",
      }),
    );
    const mapped = mapAuditDecision(result);
    console.log(`  Core 决策 : ${result.decision} (risk: ${result.risk_level})`);
    console.log(`  原因      : ${result.reason}`);
    console.log(`  命中规则  : ${result.matched_rules.join(", ")}`);
    if (mapped.requireApproval) {
      console.log(`  审批信息  : ${mapped.requireApproval.title}`);
      console.log("  ✅ 通过 — 外部请求触发人工审批");
      passed++;
    } else {
      console.log(`  ⚠️  预期 ASK，实际 ${result.decision}`);
      failed++;
    }
  } catch (err) {
    console.log(`  ❌ 异常: ${err instanceof Error ? err.message : String(err)}`);
    failed++;
  }

  // ====== 场景 5: Core 关闭后高危命令 → 本地降级 BLOCK ======
  console.log("");
  console.log("━".repeat(50));
  console.log("场景 5: 模拟 Core 不可用，高危命令降级处理");
  console.log("━".repeat(50));
  try {
    // 连接一个不存在的地址模拟 Core 不可用
    const deadClient = new AuditClient({
      baseUrl: "http://127.0.0.1:19999",
      timeoutMs: 500,
    });

    const request = makeRequest({
      tool_name: "shell",
      tool_kind: "shell_exec",
      raw_params: { cmd: "rm -rf /tmp/demo" },
      risk_hint: "file_delete",
    });

    let coreFailed = false;
    try {
      await deadClient.auditToolCall(request);
    } catch {
      coreFailed = true;
      console.log("  Core 请求 : 超时/不可达 (预期)");
    }

    if (coreFailed && config.fallback_enabled) {
      const fallback = evaluateFallbackPolicy(request, config);
      console.log(`  降级决策 : ${fallback.decision} (risk: ${fallback.risk_level})`);
      console.log(`  原因      : ${fallback.reason}`);
      console.log(`  fallback 标记: ${fallback.fallback_used}`);
      if (fallback.decision === "BLOCK" && fallback.fallback_used) {
        console.log("  ✅ 通过 — Core 不可用时高危命令被本地降级阻断");
        passed++;
      } else {
        console.log("  ⚠️  降级决策不符合预期");
        failed++;
      }
    } else {
      console.log("  ⚠️  Core 未按预期失败");
      failed++;
    }
  } catch (err) {
    console.log(`  ❌ 异常: ${err instanceof Error ? err.message : String(err)}`);
    failed++;
  }

  // ====== 结果汇总 ======
  console.log("");
  console.log("═".repeat(50));
  console.log(`  结果: ${passed} 通过 / ${failed} 失败 / ${passed + failed} 总计`);
  console.log("═".repeat(50));

  if (failed === 0) {
    console.log("  🎉 所有演示场景通过！");
  } else {
    console.log(
      `  ⚠️  ${failed} 个场景未通过，请检查 Mock Core 是否正常运行在 ${config.core_base_url}`,
    );
  }

  process.exit(failed > 0 ? 1 : 0);
}

function makeRequest(overrides: Partial<AuditRequest>): AuditRequest {
  return {
    request_id: createId("audit"),
    schema_version: "v1",
    session_id: "demo-session",
    run_id: "demo-run",
    trace_id: "demo-trace",
    tool_call_id: createId("tool"),
    tool_name: "unknown",
    tool_kind: "unknown",
    raw_params: {},
    param_summary: {},
    context: {},
    ...overrides,
  };
}

main().catch((err) => {
  console.error("演示脚本异常:", err);
  process.exit(1);
});
