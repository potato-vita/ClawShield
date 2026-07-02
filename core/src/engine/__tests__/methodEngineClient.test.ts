import { afterEach, describe, expect, it } from "vitest";
import { once } from "node:events";
import { MethodEngineClient } from "../methodEngineClient.js";
import { MethodEngineProcess } from "../methodEngineProcess.js";
import { MethodEngineQueueFullError, MethodEngineTimeoutError } from "../methodEngineErrors.js";

const clients: MethodEngineClient[] = [];

afterEach(async () => {
  await Promise.all(clients.splice(0).map((client) => client.stop()));
});

describe("MethodEngineClient", () => {
  it("starts the real Python worker and correlates 100 responses", async () => {
    const client = new MethodEngineClient({ timeoutMs: 2_000, queueLimit: 128 });
    clients.push(client);
    const health = await client.start();
    expect(health.status).toBe("ok");
    const responses = await Promise.all(Array.from({ length: 100 }, () => client.health()));
    expect(responses.every((item) => item.protocol_version === "v1")).toBe(true);
    expect(client.pendingCount).toBe(0);
  });

  it("cleans pending requests after timeout and enforces queue limit", async () => {
    const workerProcess = new MethodEngineProcess({
      command: globalThis.process.execPath,
      args: ["-e", "setInterval(() => {}, 1000)"],
      cwd: globalThis.process.cwd(),
      restart: false,
    });
    const client = new MethodEngineClient({ process: workerProcess, timeoutMs: 30, queueLimit: 1 });
    clients.push(client);
    workerProcess.start();
    await once(workerProcess, "spawn");
    const waiting = client.health();
    await expect(client.health()).rejects.toBeInstanceOf(MethodEngineQueueFullError);
    await expect(waiting).rejects.toBeInstanceOf(MethodEngineTimeoutError);
    expect(client.pendingCount).toBe(0);
  });

  it("restarts after kill and becomes healthy again", async () => {
    const process = new MethodEngineProcess({ restartMinMs: 10, restartMaxMs: 20 });
    const client = new MethodEngineClient({ process, timeoutMs: 2_000 });
    clients.push(client);
    await client.start();
    const oldPid = process.pid;
    const spawned = once(process, "spawn");
    process.kill();
    await spawned;
    expect(process.pid).not.toBe(oldPid);
    await expect(client.health()).resolves.toMatchObject({ status: "ok" });
  });
});
