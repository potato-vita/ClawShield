import { TRACESHIELD_BLOCK_PREFIX } from "../policy/decisionMapper.js";
import type { PluginConfig } from "../types/config.js";
import type { HookRegistrar } from "./on.js";

export interface RegisterSecurityMiddlewareOptions {
  api: unknown;
  config: PluginConfig;
  on: HookRegistrar;
}

export function registerSecurityMiddleware(options: RegisterSecurityMiddlewareOptions): void {
  const { api, config, on } = options;
  const typedApi = api as {
    registerAgentToolResultMiddleware?: (middleware: unknown, options?: unknown) => void;
    registerSecurityAuditCollector: (collector: unknown) => void;
  };

  on(
    api,
    "before_prompt_build",
    () => ({
      appendSystemContext: [
        "TraceShield security plugin guidance:",
        `If a tool result starts with "${TRACESHIELD_BLOCK_PREFIX}", the requested operation was blocked and not executed.`,
        "In that case, tell the user clearly that TraceShield blocked the tool call. Do not say the task is complete.",
      ].join("\n"),
    }),
    { priority: 60, timeoutMs: 1_000 },
  );

  typedApi.registerAgentToolResultMiddleware?.(
    (event: {
      result?: {
        content?: Array<{ type?: string; text?: string }>;
        details?: unknown;
      };
    }) => {
      const text =
        event.result?.content
          ?.map((entry) => (entry.type === "text" ? (entry.text ?? "") : ""))
          .join("\n") ?? "";

      if (!text.startsWith(TRACESHIELD_BLOCK_PREFIX)) {
        return undefined;
      }

      return {
        result: {
          ...event.result,
          content: [
            {
              type: "text",
              text: [
                text,
                "",
                "Visible outcome: TraceShield blocked this tool call before execution.",
              ].join("\n"),
            },
          ],
          details: {
            status: "blocked",
            source: "traceshield-security-plugin",
            reason: text,
          },
        },
      };
    },
    { runtimes: ["openclaw"] },
  );

  typedApi.registerSecurityAuditCollector(() => [
    {
      checkId: "traceshield-openclaw-plugin-enabled",
      title: "TraceShield plugin is enabled",
      severity: "info",
      detail: `TraceShield audits before_tool_call via ${config.core_base_url}`,
    },
  ]);
}
