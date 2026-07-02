import { describe, expect, it } from "vitest";
import { assembleTraceFromEvents } from "../traceAssembler.js";

const event = (step: number, status: "pending" | "completed" = "completed", hash: string | null = "h") => ({
  step_id: step,
  tool_name: "read_file",
  tool_kind: "file_read",
  args: {},
  observation: hash ? "preview" : null,
  observation_hash: hash,
  status,
});

describe("assembleTraceFromEvents", () => {
  it("orders out-of-order events by step sequence", () => {
    expect(assembleTraceFromEvents([event(3), event(1), event(2)]).events.map((item) => item.step_id)).toEqual([1, 2, 3]);
  });

  it("marks missing steps", () => {
    expect(assembleTraceFromEvents([event(1), event(3)]).trace_completeness).toBe("missing_steps");
  });

  it("marks a previous observation pending", () => {
    expect(assembleTraceFromEvents([event(1, "completed", null), event(2, "pending")]).trace_completeness).toBe(
      "previous_observation_pending",
    );
  });
});

