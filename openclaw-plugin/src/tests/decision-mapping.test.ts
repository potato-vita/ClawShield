import { describe, expect, it } from "vitest";
import { TRACESHIELD_BLOCK_PREFIX, mapAuditDecision } from "../policy/decisionMapper.js";
import type { AuditDecision } from "../types/decision.js";

describe("decision mapping", () => {
  it("allows ALLOW decisions", () => {
    const result = mapAuditDecision(decision("ALLOW"));
    expect(result.block).toBeUndefined();
    expect(result.requireApproval).toBeUndefined();
  });

  it("maps WARN to warning without blocking", () => {
    const result = mapAuditDecision(decision("WARN", "be careful"));
    expect(result.warning).toBe("be careful");
    expect(result.block).toBeUndefined();
  });

  it("maps ASK to requireApproval", () => {
    const result = mapAuditDecision({
      ...decision("ASK"),
      approval: {
        approval_id: "ap1",
        title: "Approve",
        description: "Need approval",
        default_action: "BLOCK",
        timeout_ms: 1000,
      },
    });

    expect(result.requireApproval?.approvalId).toBe("ap1");
  });

  it("maps BLOCK to block result", () => {
    const result = mapAuditDecision(decision("BLOCK", "blocked"));
    expect(result.block).toBe(true);
    expect(result.blockReason).toContain(TRACESHIELD_BLOCK_PREFIX);
    expect(result.blockReason).toContain("Reason: blocked");
    expect(result.blockReason).toContain("Do not summarize it as completed.");
  });

  it("maps modified params", () => {
    const result = mapAuditDecision({
      ...decision("ALLOW"),
      modified_params: { cmd: "ls" },
    });
    expect(result.modifiedParams).toEqual({ cmd: "ls" });
  });
});

function decision(kind: AuditDecision["decision"], reason = "ok"): AuditDecision {
  return {
    decision: kind,
    risk_level: "low",
    reason,
    matched_rules: ["test"],
  };
}
