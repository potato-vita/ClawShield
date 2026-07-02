import { randomUUID } from "node:crypto";
import type { MethodResponse } from "./methodEngineProtocol.js";
import { parseMethodResponse } from "./methodEngineProtocol.js";
import { MethodEngineProcess } from "./methodEngineProcess.js";
import {
  MethodEngineProtocolError,
  MethodEngineQueueFullError,
  MethodEngineTimeoutError,
  MethodEngineUnavailableError,
} from "./methodEngineErrors.js";

interface Pending {
  resolve: (response: MethodResponse) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export interface MethodEngineClientOptions {
  process?: MethodEngineProcess;
  timeoutMs?: number;
  queueLimit?: number;
  startupTimeoutMs?: number;
}

export class MethodEngineClient {
  readonly process: MethodEngineProcess;
  private readonly pending = new Map<string, Pending>();
  private readonly timeoutMs: number;
  private readonly queueLimit: number;
  private readonly startupTimeoutMs: number;

  constructor(options: MethodEngineClientOptions = {}) {
    this.process = options.process ?? new MethodEngineProcess();
    this.timeoutMs = options.timeoutMs ?? 120;
    this.queueLimit = options.queueLimit ?? 256;
    this.startupTimeoutMs = options.startupTimeoutMs ?? 3_000;
    this.process.on("line", (line: string) => this.handleLine(line));
    this.process.on("exit", () => this.failPending(new MethodEngineUnavailableError("Method worker exited")));
    this.process.on("protocolError", (error: Error) => this.failPending(error));
  }

  async start(): Promise<Record<string, unknown>> {
    this.process.start();
    return this.request("health", undefined, this.startupTimeoutMs);
  }

  request(
    method: "health" | "evaluate_runtime_trace" | "detect_observation" | "shutdown",
    params?: Record<string, unknown>,
    timeoutMs = this.timeoutMs,
  ): Promise<Record<string, unknown>> {
    if (this.pending.size >= this.queueLimit) {
      return Promise.reject(new MethodEngineQueueFullError("Method worker queue is full"));
    }
    const requestId = `method_req_${randomUUID()}`;
    return new Promise((resolveRequest, rejectRequest) => {
      const timer = setTimeout(() => {
        this.pending.delete(requestId);
        rejectRequest(new MethodEngineTimeoutError(`Method request timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(requestId, {
        resolve: (response) => {
          if (!response.ok) {
            rejectRequest(new MethodEngineProtocolError(`${response.error?.code}: ${response.error?.message}`));
          } else {
            resolveRequest(response.result ?? {});
          }
        },
        reject: rejectRequest,
        timer,
      });
      const sent = this.process.send(
        JSON.stringify({ protocol_version: "v1", request_id: requestId, method, ...(params ? { params } : {}) }),
      );
      if (!sent) {
        clearTimeout(timer);
        this.pending.delete(requestId);
        rejectRequest(new MethodEngineUnavailableError("Method worker is unavailable"));
      }
    });
  }

  health(): Promise<Record<string, unknown>> {
    return this.request("health", undefined, this.startupTimeoutMs);
  }

  async stop(): Promise<void> {
    try {
      if (this.process.pid) await this.request("shutdown", undefined, 1_000);
    } catch {
      // Process stop below is authoritative.
    }
    await this.process.stop();
    this.failPending(new MethodEngineUnavailableError("Method client stopped"));
  }

  get pendingCount(): number {
    return this.pending.size;
  }

  private handleLine(line: string): void {
    let response: MethodResponse;
    try {
      response = parseMethodResponse(line);
    } catch (error) {
      this.failPending(new MethodEngineProtocolError(`Invalid worker response: ${String(error)}`));
      return;
    }
    const pending = this.pending.get(response.request_id);
    if (!pending) return;
    clearTimeout(pending.timer);
    this.pending.delete(response.request_id);
    pending.resolve(response);
  }

  private failPending(error: Error): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
}
