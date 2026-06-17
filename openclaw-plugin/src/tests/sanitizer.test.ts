import { describe, expect, it } from "vitest";
import { sha256 } from "../sanitizer/hash.js";
import { previewText } from "../sanitizer/preview.js";
import { redactObject, redactText } from "../sanitizer/redact.js";

describe("sanitizer", () => {
  it("redacts secret assignments", () => {
    expect(redactText("token=abc123")).toContain("token=[REDACTED]");
  });

  it("redacts private keys", () => {
    const text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----";
    expect(redactText(text)).toBe("[REDACTED_PRIVATE_KEY]");
  });

  it("hashes sensitive object fields", () => {
    const value = redactObject({ password: "secret", normal: "ok" });
    expect(value.password).toEqual({
      redacted: "true",
      hash: sha256("secret").slice(0, 16),
    });
    expect(value.normal).toBe("ok");
  });

  it("truncates long previews", () => {
    expect(previewText("a".repeat(600))).toContain("[TRUNCATED:100]");
  });
});
