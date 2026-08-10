import Fastify from "fastify";
import { afterEach, describe, expect, it } from "vitest";
import { createAssistantRoutes } from "../assistant.js";

const apps: ReturnType<typeof Fastify>[] = [];

async function buildTestApp(fetchImpl: typeof fetch, timeoutMs = 1_000) {
  const app = Fastify({ logger: false });
  apps.push(app);
  await app.register(
    createAssistantRoutes({
      baseUrl: "http://assistant.test:8790",
      timeoutMs,
      fetchImpl,
    }),
  );
  await app.ready();
  return app;
}

afterEach(async () => {
  await Promise.all(apps.splice(0).map(async (app) => app.close()));
});

describe("assistant proxy routes", () => {
  it("rejects malformed chat requests without contacting the upstream", async () => {
    let upstreamCalls = 0;
    const fetchImpl: typeof fetch = async () => {
      upstreamCalls += 1;
      return new Response();
    };
    const app = await buildTestApp(fetchImpl);

    const response = await app.inject({
      method: "POST",
      url: "/v1/assistant/chat/stream",
      payload: {
        message: "",
        history: [{ role: "system", content: "not accepted" }],
      },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().error).toBe("invalid_assistant_request");
    expect(upstreamCalls).toBe(0);
  });

  it("returns only validated assistant health fields", async () => {
    const fetchImpl: typeof fetch = async () =>
      new Response(
        JSON.stringify({
          ok: true,
          service: "traceshield-assistant",
          framework: "cloudwego-eino",
          provider: "deepseek",
          model: "test-model",
          configured: true,
          internal_debug: "must not cross the proxy",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    const app = await buildTestApp(fetchImpl);

    const response = await app.inject({ method: "GET", url: "/v1/assistant/health" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({
      ok: true,
      service: "traceshield-assistant",
      framework: "cloudwego-eino",
      provider: "deepseek",
      model: "test-model",
      configured: true,
    });
  });

  it("forwards the validated body and streams the upstream SSE response", async () => {
    const upstreamEvents = [
      'event: start\ndata: {"conversation_id":"conv-1","model":"test-model"}\n\n',
      'event: delta\ndata: {"content":"hello"}\n\n',
      'event: done\ndata: {"conversation_id":"conv-1"}\n\n',
    ].join("");
    let requestInit: RequestInit | undefined;
    const fetchImpl: typeof fetch = async (_input, init) => {
      requestInit = init;
      return new Response(upstreamEvents, {
        status: 200,
        headers: { "content-type": "text/event-stream; charset=utf-8" },
      });
    };
    const app = await buildTestApp(fetchImpl);
    const payload = {
      conversation_id: "conv-1",
      message: "Summarize this incident",
      history: [{ role: "user" as const, content: "Earlier message" }],
      context: { run_id: "run-1" },
      ignored: "not forwarded",
    };

    const response = await app.inject({
      method: "POST",
      url: "/v1/assistant/chat/stream",
      payload,
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers["access-control-allow-origin"]).toBe("*");
    expect(response.headers["content-type"]).toContain("text/event-stream");
    expect(response.body).toBe(upstreamEvents);
    expect(JSON.parse(String(requestInit?.body))).toEqual({
      conversation_id: "conv-1",
      message: "Summarize this incident",
      history: [{ role: "user", content: "Earlier message" }],
      context: { run_id: "run-1" },
    });
  });

  it("does not expose an upstream error body", async () => {
    const fetchImpl: typeof fetch = async () =>
      new Response("provider secret diagnostic", { status: 500 });
    const app = await buildTestApp(fetchImpl);

    const response = await app.inject({
      method: "POST",
      url: "/v1/assistant/chat/stream",
      payload: { message: "hello" },
    });

    expect(response.statusCode).toBe(502);
    expect(response.json()).toEqual({
      error: "assistant_unavailable",
      message: "The assistant service is unavailable.",
    });
    expect(response.body).not.toContain("provider secret diagnostic");
  });

  it("returns a stable timeout error when the upstream does not respond", async () => {
    const fetchImpl: typeof fetch = async (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("upstream detail", "AbortError")),
          { once: true },
        );
      });
    const app = await buildTestApp(fetchImpl, 10);

    const response = await app.inject({
      method: "POST",
      url: "/v1/assistant/chat/stream",
      payload: { message: "hello" },
    });

    expect(response.statusCode).toBe(504);
    expect(response.json()).toEqual({
      error: "assistant_timeout",
      message: "The assistant service timed out.",
    });
    expect(response.body).not.toContain("upstream detail");
  });

  it("aborts the upstream request when the downstream client disconnects", async () => {
    let markUpstreamAborted: (() => void) | undefined;
    const upstreamAborted = new Promise<void>((resolve) => {
      markUpstreamAborted = resolve;
    });
    const encoder = new TextEncoder();
    const fetchImpl: typeof fetch = async (_input, init) => {
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            encoder.encode('event: start\ndata: {"conversation_id":"conv-1","model":"test"}\n\n'),
          );
          init?.signal?.addEventListener(
            "abort",
            () => {
              markUpstreamAborted?.();
              controller.error(new DOMException("Aborted", "AbortError"));
            },
            { once: true },
          );
        },
      });
      return new Response(stream, {
        headers: { "content-type": "text/event-stream; charset=utf-8" },
      });
    };
    const app = await buildTestApp(fetchImpl);
    const origin = await app.listen({ host: "127.0.0.1", port: 0 });
    const downstreamController = new AbortController();
    const response = await fetch(`${origin}/v1/assistant/chat/stream`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "hello" }),
      signal: downstreamController.signal,
    });
    await response.body?.getReader().read();
    downstreamController.abort();

    let timer: ReturnType<typeof setTimeout> | undefined;
    const observed = await Promise.race([
      upstreamAborted.then(() => true),
      new Promise<boolean>((resolve) => {
        timer = setTimeout(() => resolve(false), 1_000);
      }),
    ]);
    if (timer) clearTimeout(timer);
    expect(observed).toBe(true);
  });
});
