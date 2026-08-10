import type { ServerResponse } from "node:http";
import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { config } from "../config.js";

const assistantMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string().min(1).max(32_000),
});

const assistantChatSchema = z.object({
  conversation_id: z.string().min(1).max(300).optional(),
  message: z.string().min(1).max(32_000),
  history: z.array(assistantMessageSchema).max(100).optional(),
  context: z.record(z.unknown()).optional(),
});

const assistantHealthSchema = z.object({
  ok: z.boolean(),
  service: z.string().min(1).max(100),
  framework: z.string().min(1).max(100),
  provider: z.string().min(1).max(100),
  model: z.string().min(1).max(200),
  configured: z.boolean(),
});

export interface AssistantRouteOptions {
  baseUrl: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

function assistantUrl(baseUrl: string, path: string): string {
  return new URL(path, `${baseUrl.replace(/\/+$/, "")}/`).toString();
}

function publicProxyError(error: "assistant_unavailable" | "assistant_timeout") {
  if (error === "assistant_timeout") {
    return {
      error,
      message: "The assistant service timed out.",
    } as const;
  }
  return {
    error,
    message: "The assistant service is unavailable.",
  } as const;
}

function streamError(code: string, message: string): string {
  return `event: error\ndata: ${JSON.stringify({ code, message })}\n\n`;
}

async function waitForDrainOrClose(response: ServerResponse): Promise<boolean> {
  if (response.destroyed || response.writableEnded) return false;

  return new Promise((resolve) => {
    const cleanup = () => {
      response.off("drain", onDrain);
      response.off("close", onClose);
      response.off("error", onClose);
    };
    const onDrain = () => {
      cleanup();
      resolve(true);
    };
    const onClose = () => {
      cleanup();
      resolve(false);
    };

    response.once("drain", onDrain);
    response.once("close", onClose);
    response.once("error", onClose);
  });
}

async function writeChunk(response: ServerResponse, chunk: Uint8Array | string): Promise<boolean> {
  if (response.destroyed || response.writableEnded) return false;
  if (response.write(chunk)) return true;
  return waitForDrainOrClose(response);
}

export function createAssistantRoutes(options: AssistantRouteOptions) {
  const fetchImpl = options.fetchImpl ?? fetch;

  return async function assistantRoutes(app: FastifyInstance): Promise<void> {
    app.get("/v1/assistant/health", async (request, reply) => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), options.timeoutMs);

      try {
        const upstream = await fetchImpl(assistantUrl(options.baseUrl, "/health"), {
          headers: { accept: "application/json" },
          signal: controller.signal,
        });
        if (!upstream.ok) {
          request.log.warn({ status: upstream.status }, "Assistant health upstream returned an error");
          return reply.code(503).send(publicProxyError("assistant_unavailable"));
        }

        const parsed = assistantHealthSchema.safeParse(await upstream.json());
        if (!parsed.success) {
          request.log.warn("Assistant health upstream returned an invalid response");
          return reply.code(502).send(publicProxyError("assistant_unavailable"));
        }
        return parsed.data;
      } catch (error) {
        request.log.warn({ err: error }, "Assistant health upstream request failed");
        return reply
          .code(controller.signal.aborted ? 504 : 503)
          .send(publicProxyError(controller.signal.aborted ? "assistant_timeout" : "assistant_unavailable"));
      } finally {
        clearTimeout(timeout);
      }
    });

    app.post("/v1/assistant/chat/stream", async (request, reply) => {
      const parsed = assistantChatSchema.safeParse(request.body);
      if (!parsed.success) {
        return reply.code(400).send({
          error: "invalid_assistant_request",
          details: parsed.error.flatten(),
        });
      }

      const controller = new AbortController();
      let timedOut = false;
      let downstreamClosed = false;
      const timeout = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, options.timeoutMs);
      const closeUpstream = () => {
        downstreamClosed = true;
        controller.abort();
      };
      request.raw.once("aborted", closeUpstream);
      reply.raw.once("close", closeUpstream);

      let upstream: Response;
      try {
        upstream = await fetchImpl(assistantUrl(options.baseUrl, "/v1/chat/stream"), {
          method: "POST",
          headers: {
            accept: "text/event-stream",
            "content-type": "application/json",
          },
          body: JSON.stringify(parsed.data),
          signal: controller.signal,
        });
      } catch (error) {
        clearTimeout(timeout);
        request.raw.off("aborted", closeUpstream);
        reply.raw.off("close", closeUpstream);
        if (downstreamClosed) return reply;
        request.log.warn({ err: error }, "Assistant chat upstream request failed");
        return reply
          .code(timedOut ? 504 : 503)
          .send(publicProxyError(timedOut ? "assistant_timeout" : "assistant_unavailable"));
      }

      if (!upstream.ok || !upstream.body) {
        clearTimeout(timeout);
        request.raw.off("aborted", closeUpstream);
        reply.raw.off("close", closeUpstream);
        request.log.warn({ status: upstream.status }, "Assistant chat upstream returned an error");
        await upstream.body?.cancel().catch(() => undefined);
        return reply
          .code(upstream.status === 429 ? 429 : 502)
          .send(
            upstream.status === 429
              ? { error: "assistant_rate_limited", message: "The assistant service is rate limited." }
              : publicProxyError("assistant_unavailable"),
          );
      }

      const contentType = upstream.headers.get("content-type")?.toLowerCase() ?? "";
      if (!contentType.startsWith("text/event-stream")) {
        clearTimeout(timeout);
        request.raw.off("aborted", closeUpstream);
        reply.raw.off("close", closeUpstream);
        await upstream.body.cancel().catch(() => undefined);
        request.log.warn({ contentType }, "Assistant chat upstream returned a non-SSE response");
        return reply.code(502).send(publicProxyError("assistant_unavailable"));
      }

      reply.hijack();
      const response = reply.raw;
      response.writeHead(200, {
        "access-control-allow-origin": "*",
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache, no-transform",
        connection: "keep-alive",
        "x-accel-buffering": "no",
      });

      const reader = upstream.body.getReader();
      try {
        while (!downstreamClosed) {
          const result = await reader.read();
          if (result.done) break;
          if (!(await writeChunk(response, result.value))) break;
        }
      } catch (error) {
        if (!downstreamClosed) {
          request.log.warn({ err: error }, "Assistant chat upstream stream failed");
          const code = timedOut ? "assistant_timeout" : "assistant_stream_error";
          const message = timedOut
            ? "The assistant service timed out."
            : "The assistant stream was interrupted.";
          await writeChunk(response, streamError(code, message));
        }
      } finally {
        clearTimeout(timeout);
        request.raw.off("aborted", closeUpstream);
        reply.raw.off("close", closeUpstream);
        if (downstreamClosed) {
          await reader.cancel().catch(() => undefined);
        }
        if (!response.destroyed && !response.writableEnded) response.end();
      }
    });
  };
}

export async function registerAssistantRoutes(app: FastifyInstance): Promise<void> {
  return createAssistantRoutes({
    baseUrl: config.assistantBaseUrl,
    timeoutMs: config.assistantTimeoutMs,
  })(app);
}
