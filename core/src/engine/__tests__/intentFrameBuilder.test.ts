import { describe, expect, it } from "vitest";
import { buildIntentFrame } from "../intentFrameBuilder.js";
import type { AuditRequest } from "../../types/pluginContract.js";

const request = (userGoal?: string): AuditRequest => ({
  request_id: "r",
  schema_version: "v1",
  session_id: "s",
  run_id: "run",
  trace_id: "t",
  tool_call_id: "tc",
  tool_name: "read_file",
  tool_kind: "file_read",
  raw_params: {},
  param_summary: {},
  context: { ...(userGoal ? { user_goal: userGoal } : {}), workspace_root: "/work" },
});

describe("buildIntentFrame", () => {
  it("versions a high-confidence audit goal", () => {
    expect(buildIntentFrame(request("read docs"))).toMatchObject({
      version: "intent-v1",
      source: "audit_context",
      confidence: "high",
    });
  });

  it("falls back to a message summary", () => {
    expect(buildIntentFrame(request(), "recent user goal")).toMatchObject({
      source: "message_summary",
      confidence: "medium",
    });
  });
});

