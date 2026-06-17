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

  it("redacts secrets after long prefix (regression: redact before truncate)", () => {
    // 模拟真实对话中敏感信息出现在消息中段
    const prefix = "Here is some context text. ".repeat(10); // ~290 chars
    const sensitive = " my password=super_secret_12345 and more text";
    const text = prefix + sensitive;
    const redacted = redactText(text);
    // 敏感信息已被脱敏（有单词边界）
    expect(redacted).toContain("password=[REDACTED]");
    expect(redacted).not.toContain("super_secret_12345");
  });

  it("never leaks secrets even when they appear beyond the preview window", () => {
    // 敏感内容在 500 字符之后：脱敏后可能被截断，但原始 secret 绝不出现
    const prefix = "x".repeat(600);
    const text = prefix + " token=abc123secret";
    const redacted = redactText(text);
    // 核心保障：原始密钥不出现在输出中
    expect(redacted).not.toContain("abc123secret");
    expect(redacted.length).toBeLessThanOrEqual(550);
  });
});
