import { describe, expect, it } from "vitest";
import { defaultPluginConfig } from "../types/config.js";
import { normalizeMessage } from "../events/normalizeMessage.js";
import { buildAuditRequest } from "../events/normalizeToolCall.js";

describe("plugin contract", () => {
  it("creates v1 trace events", () => {
    const event = normalizeMessage(
      "message_received",
      {
        session_id: "s1",
        run_id: "r1",
        trace_id: "t1",
        role: "user",
        content: "hello",
      },
      defaultPluginConfig,
    );

    expect(event.schema_version).toBe("v1");
    expect(event.type).toBe("message_received");
    expect(event.mode).toBe("async");
    expect(event.session_id).toBe("s1");
  });

  it("creates v1 audit requests", () => {
    const request = buildAuditRequest({
      session_id: "s1",
      run_id: "r1",
      trace_id: "t1",
      tool_call_id: "tc1",
      tool_name: "shell",
      params: { cmd: "ls" },
    });

    expect(request.schema_version).toBe("v1");
    expect(request.tool_kind).toBe("shell_exec");
    expect(request.raw_params).toEqual({ cmd: "ls" });
  });
});
