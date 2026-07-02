import { describe, expect, it } from "vitest";
import { parseMethodResponse } from "../methodEngineProtocol.js";

describe("method engine protocol", () => {
  it("rejects malformed worker responses", () => {
    expect(() => parseMethodResponse('{"ok":true}')).toThrow();
  });

  it("accepts a versioned response", () => {
    expect(
      parseMethodResponse('{"protocol_version":"v1","request_id":"r","ok":true,"result":{}}'),
    ).toMatchObject({ request_id: "r", ok: true });
  });
});

