import { describe, expect, it } from "vitest";
import { getSharedEventQueue } from "../runtime/sharedEventQueue.js";

describe("shared event queue", () => {
  it("reuses one process-wide queue across plugin registrations", () => {
    const first = getSharedEventQueue(1000);
    const second = getSharedEventQueue(1000);

    expect(second).toBe(first);
  });
});
