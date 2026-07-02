import { EventEmitter } from "node:events";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { resolve } from "node:path";
import { createInterface } from "node:readline";

export interface MethodEngineProcessOptions {
  command?: string;
  args?: string[];
  cwd?: string;
  maxLineBytes?: number;
  restart?: boolean;
  restartMinMs?: number;
  restartMaxMs?: number;
  onStderr?: (line: string) => void;
}

interface ResolvedProcessOptions {
  command: string;
  args: string[];
  cwd: string;
  maxLineBytes: number;
  restart: boolean;
  restartMinMs: number;
  restartMaxMs: number;
  onStderr: ((line: string) => void) | undefined;
}

export class MethodEngineProcess extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | undefined;
  private stopping = false;
  private restartDelay: number;
  private restartTimer: ReturnType<typeof setTimeout> | undefined;
  readonly options: ResolvedProcessOptions;

  constructor(options: MethodEngineProcessOptions = {}) {
    super();
    const methodDir = resolve(process.cwd(), "method-engine");
    this.options = {
      command: options.command ?? resolve(methodDir, ".venv/bin/python"),
      args: options.args ?? [resolve(methodDir, "python/traceshield_method/worker.py")],
      cwd: options.cwd ?? methodDir,
      maxLineBytes: options.maxLineBytes ?? 4 * 1024 * 1024,
      restart: options.restart ?? true,
      restartMinMs: options.restartMinMs ?? 100,
      restartMaxMs: options.restartMaxMs ?? 5_000,
      onStderr: options.onStderr,
    };
    this.restartDelay = this.options.restartMinMs;
  }

  start(): void {
    if (this.child) return;
    this.stopping = false;
    const child = spawn(this.options.command, this.options.args, {
      cwd: this.options.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
    this.child = child;
    const stdout = createInterface({ input: child.stdout, crlfDelay: Infinity });
    const stderr = createInterface({ input: child.stderr, crlfDelay: Infinity });
    stdout.on("line", (line) => {
      if (Buffer.byteLength(line) > this.options.maxLineBytes) {
        this.emit("protocolError", new Error("Method worker response exceeded max line size"));
        return;
      }
      this.emit("line", line);
    });
    stderr.on("line", (line) => this.options.onStderr?.(line));
    child.once("spawn", () => {
      this.restartDelay = this.options.restartMinMs;
      this.emit("spawn", child.pid);
    });
    child.once("error", (error) => this.emit("processError", error));
    child.once("exit", (code, signal) => {
      this.child = undefined;
      this.emit("exit", code, signal);
      if (!this.stopping && this.options.restart) this.scheduleRestart();
    });
  }

  send(line: string): boolean {
    if (!this.child?.stdin.writable) return false;
    return this.child.stdin.write(`${line}\n`);
  }

  kill(signal: NodeJS.Signals = "SIGKILL"): void {
    this.child?.kill(signal);
  }

  async stop(): Promise<void> {
    this.stopping = true;
    if (this.restartTimer) clearTimeout(this.restartTimer);
    const child = this.child;
    if (!child) return;
    await new Promise<void>((resolveStop) => {
      const timer = setTimeout(() => child.kill("SIGKILL"), 1_000);
      child.once("exit", () => {
        clearTimeout(timer);
        resolveStop();
      });
      child.stdin.end();
    });
  }

  get pid(): number | undefined {
    return this.child?.pid;
  }

  private scheduleRestart(): void {
    this.restartTimer = setTimeout(() => this.start(), this.restartDelay);
    this.restartDelay = Math.min(this.restartDelay * 2, this.options.restartMaxMs);
  }
}
