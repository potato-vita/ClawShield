import { describe, expect, it } from "vitest";
import { combineWithSafetyFloor } from "../decisionCombiner.js";
import { evaluateSafetyFloor } from "../safetyFloor.js";

const decision = (value: "ALLOW" | "WARN" | "ASK" | "BLOCK") => ({
  decision: value,
  riskLevel: value === "BLOCK" ? "critical" as const : "low" as const,
  reason: value,
  matchedRules: [value.toLowerCase()],
  approval: null,
});

describe("enforce decision safety", () => {
  it("never lowers a safety floor", () => {
    expect(combineWithSafetyFloor(decision("ALLOW"), decision("BLOCK")).decision).toBe("BLOCK");
  });

  it("does not let a weaker floor lower the method", () => {
    expect(combineWithSafetyFloor(decision("BLOCK"), decision("ASK")).decision).toBe("BLOCK");
  });

  it("recognizes explicit secret access", () => {
    expect(
      evaluateSafetyFloor({
        request_id: "r",
        schema_version: "v1",
        session_id: "s",
        run_id: "run",
        trace_id: "t",
        tool_call_id: "tc",
        tool_name: "read_file",
        tool_kind: "file_read",
        raw_params: { path: ".env" },
        param_summary: {},
        context: {},
      })?.decision,
    ).toBe("BLOCK");
  });
});

