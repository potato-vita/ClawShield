import { describe, expect, it } from "vitest";
import { RunContextRegistry } from "../runtime/runContextRegistry.js";

describe("RunContextRegistry", () => {
  it("keeps generated IDs and step sequence stable across before/after", () => {
    const registry = new RunContextRegistry();
    const first = registry.beginToolCall({ tool_name: "read_file", workspace_root: "/work" });
    const second = registry.beginToolCall({ tool_name: "shell", workspace_root: "/work" });
    const completedSecond = registry.completeToolCall({ tool_name: "shell", workspace_root: "/work" });
    const completedFirst = registry.completeToolCall({ tool_name: "read_file", workspace_root: "/work" });

    expect([first.step_seq, second.step_seq]).toEqual([1, 2]);
    expect(completedSecond).toMatchObject({ tool_call_id: second.tool_call_id, step_seq: 2 });
    expect(completedFirst).toMatchObject({ tool_call_id: first.tool_call_id, step_seq: 1 });
    expect(first.run_id).toBe(second.run_id);
  });

  it("does not allocate a second step for an explicit tool-call retry", () => {
    const registry = new RunContextRegistry();
    const input = { session_id: "s", run_id: "r", trace_id: "t", tool_call_id: "tc", tool_name: "read" };
    expect(registry.beginToolCall(input)).toEqual(registry.beginToolCall(input));
  });

  it("starts a new generated run after agent end", () => {
    const registry = new RunContextRegistry();
    const first = registry.resolveRun({ session_id: "s" });
    registry.endRun(first);
    const next = registry.resolveRun({ session_id: "s" });
    expect(next.run_id).not.toBe(first.run_id);
  });
});

