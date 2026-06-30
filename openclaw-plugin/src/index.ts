import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { AuditClient } from "./client/auditClient.js";
import { loadConfig } from "./config.js";
import { createLogger } from "./logger.js";
import { on } from "./register/on.js";
import { registerFlushWorker } from "./register/registerFlushWorker.js";
import { registerMessageHooks } from "./register/registerMessageHooks.js";
import { registerSecurityMiddleware } from "./register/registerSecurityMiddleware.js";
import { registerStatusTool } from "./register/registerStatusTool.js";
import { registerToolHooks } from "./register/registerToolHooks.js";
import { getSharedEventQueue } from "./runtime/sharedEventQueue.js";

const pluginEntry: unknown = definePluginEntry({
  id: "traceshield-security-plugin",
  name: "TraceShield Security Plugin",
  description: "Runtime security gate for OpenClaw tool calls and trace events.",
  register(api) {
    const config = loadConfig(api.pluginConfig ?? {});
    const logger = createLogger("traceshield-openclaw");
    const queue = getSharedEventQueue(config.memory_queue_max_events);
    const auditClient = new AuditClient({
      baseUrl: config.core_base_url,
      timeoutMs: config.audit_timeout_ms,
    });

    registerStatusTool({ api, config, queue });
    registerFlushWorker({ api, config, queue });
    registerSecurityMiddleware({ api, config, on });
    registerMessageHooks({ api, queue, config, on });
    registerToolHooks({ api, queue, config, logger, auditClient, on });

    api.logger.info(
      `TraceShield Security Plugin registered core=${config.core_base_url} auditTimeoutMs=${config.audit_timeout_ms} fallback=${config.fallback_enabled}`,
    );
  },
});

export default pluginEntry;
