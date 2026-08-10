import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { resolve } from "node:path";
import { test } from "node:test";

test("public gateway only permits the assistant streaming write", async (t) => {
  const received = [];
  const core = createServer(async (request, response) => {
    const body = await readBody(request);
    received.push({ method: request.method, url: request.url, body });

    if (request.method === "POST" && request.url === "/v1/assistant/chat/stream") {
      response.writeHead(200, {
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache, no-transform",
        "x-accel-buffering": "no",
      });
      response.write('event: start\ndata: {"model":"test-model"}\n\n');
      setTimeout(() => {
        response.write('event: delta\ndata: {"content":"ok"}\n\n');
        setTimeout(() => response.end('event: done\ndata: {"finish_reason":"stop"}\n\n'), 40);
      }, 40);
      return;
    }

    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ ok: true }));
  });
  const web = createServer((_request, response) => response.end("TraceShield"));
  const coreOrigin = await listen(core);
  const webOrigin = await listen(web);

  const gateway = spawn(process.execPath, [resolve(import.meta.dirname, "publicGateway.mjs")], {
    env: {
      ...process.env,
      TRACESHIELD_PUBLIC_GATEWAY_HOST: "127.0.0.1",
      TRACESHIELD_PUBLIC_GATEWAY_PORT: "0",
      TRACESHIELD_WEB_ORIGIN: webOrigin,
      TRACESHIELD_CORE_ORIGIN: coreOrigin,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const gatewayOrigin = await gatewayAddress(gateway);

  t.after(async () => {
    gateway.kill("SIGTERM");
    await Promise.race([once(gateway, "exit"), delay(1_000)]);
    await closeServer(core);
    await closeServer(web);
  });

  const blocked = await fetch(`${gatewayOrigin}/v1/policies/policy-1`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ enabled: false }),
  });
  assert.equal(blocked.status, 403);
  assert.deepEqual(await blocked.json(), { error: "public_gateway_read_only" });
  assert.equal(received.length, 0, "blocked writes must not reach Core");

  const wrongMethod = await fetch(`${gatewayOrigin}/v1/assistant/chat/stream`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: "not allowed" }),
  });
  assert.equal(wrongMethod.status, 403);
  assert.equal(received.length, 0, "only POST may use the assistant stream route");

  const neighboringPath = await fetch(`${gatewayOrigin}/v1/assistant/chat/stream/extra`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: "not allowed" }),
  });
  assert.equal(neighboringPath.status, 403);
  assert.equal(received.length, 0, "the write allowlist must match the exact route");

  const requestBody = JSON.stringify({ message: "stream this", history: [] });
  const streamed = await fetch(`${gatewayOrigin}/v1/assistant/chat/stream`, {
    method: "POST",
    headers: {
      accept: "text/event-stream",
      "content-type": "application/json",
    },
    body: requestBody,
  });
  assert.equal(streamed.status, 200);
  assert.match(streamed.headers.get("content-type") ?? "", /^text\/event-stream/);
  assert.equal(streamed.headers.get("cache-control"), "no-cache, no-transform");

  const reader = streamed.body.getReader();
  const decoder = new TextDecoder();
  const first = await reader.read();
  const firstChunk = decoder.decode(first.value, { stream: true });
  assert.match(firstChunk, /event: start/);
  assert.doesNotMatch(firstChunk, /event: done/, "the gateway must not buffer the complete SSE response");

  let remainder = "";
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    remainder += decoder.decode(chunk.value, { stream: true });
  }
  remainder += decoder.decode();
  assert.match(remainder, /event: delta/);
  assert.match(remainder, /event: done/);
  assert.deepEqual(received, [{
    method: "POST",
    url: "/v1/assistant/chat/stream",
    body: requestBody,
  }]);
});

function listen(server) {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      const address = server.address();
      assert.equal(typeof address, "object");
      resolveListen(`http://127.0.0.1:${address.port}`);
    });
  });
}

function gatewayAddress(child) {
  return new Promise((resolveAddress, reject) => {
    let output = "";
    const timeout = setTimeout(() => reject(new Error(`gateway did not start: ${output}`)), 3_000);
    const consume = (chunk) => {
      output += chunk.toString();
      const match = output.match(/listening at (http:\/\/127\.0\.0\.1:\d+)/);
      if (!match) return;
      clearTimeout(timeout);
      child.stdout.off("data", consume);
      resolveAddress(match[1]);
    };
    child.stdout.on("data", consume);
    child.stderr.on("data", (chunk) => { output += chunk.toString(); });
    child.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`gateway exited with ${code}: ${output}`));
    });
  });
}

function readBody(request) {
  return new Promise((resolveBody, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => resolveBody(body));
    request.on("error", reject);
  });
}

function closeServer(server) {
  return new Promise((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()));
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}
