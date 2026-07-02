import { resolve } from "node:path";
import type { AuditDecision, AuditRequest } from "../types/pluginContract.js";
import type { MethodEvaluationResult } from "../types/methodContract.js";
import { config } from "../config.js";
import { MethodEngineClient } from "../engine/methodEngineClient.js";
import { MethodEngineProcess } from "../engine/methodEngineProcess.js";
import { MethodEngineTimeoutError } from "../engine/methodEngineErrors.js";
import { buildIntentFrame } from "../engine/intentFrameBuilder.js";
import { assembleTrace } from "../engine/traceAssembler.js";
import {
  completeMethodEvaluation,
  createMethodEvaluation,
  failMethodEvaluation,
  markMethodRunning,
} from "./methodEvaluationRepository.js";
import { classifyMethodDiff } from "./methodDiffService.js";
import { auditEventStream } from "./streamService.js";
import { pool } from "../db/pool.js";
import { recordObservationDetection } from "./observationDetectionService.js";
import { nextMethodEvaluationRevision } from "./methodEvaluationRepository.js";

export async function prepareShadowEvaluation(request: AuditRequest, revision = 1): Promise<{
  evaluationId: string;
  params: Record<string, unknown>;
}> {
  const params = await buildRuntimeParams(request);
  const traceCompleteness = String(params.trace_completeness);
  const evaluationId = await createMethodEvaluation({
    requestId: request.request_id,
    toolCallId: request.tool_call_id,
    runId: request.run_id,
    ...(request.step_seq !== undefined ? { stepSeq: request.step_seq } : {}),
    profile: config.methodProfile,
    profileVersion: config.methodProfileVersion,
    methodVersion: config.methodVersion,
    traceCompleteness,
    input: params,
    revision,
  });
  return { evaluationId, params };
}

export async function buildRuntimeParams(request: AuditRequest): Promise<Record<string, unknown>> {
  const intent = buildIntentFrame(request);
  const trace = await assembleTrace(request);
  return {
    session_id: request.session_id,
    run_id: request.run_id,
    trace_id: request.trace_id,
    current_step_seq: request.step_seq ?? 1,
    profile: config.methodProfile,
    profile_version: config.methodProfileVersion,
    method_version: config.methodVersion,
    semantic_schema_version: "v1",
    intent_frame: intent.frame,
    events: trace.events,
    trace_completeness: trace.trace_completeness,
  };
}

interface ShadowJob {
  request: AuditRequest;
  legacyDecision: AuditDecision;
  revision?: number;
}

export class MethodShadowService {
  private readonly queue: ShadowJob[] = [];
  private readonly client: MethodEngineClient;
  private running = false;
  private accepting = true;
  private available = false;

  constructor() {
    const workerProcess = new MethodEngineProcess({
      command: resolve(process.cwd(), config.methodPython),
      args: [resolve(process.cwd(), config.methodWorker)],
      cwd: resolve(process.cwd(), "method-engine"),
      onStderr: (line) => console.warn(`[method-worker] ${line}`),
    });
    this.client = new MethodEngineClient({
      process: workerProcess,
      timeoutMs: config.methodTimeoutMs,
      queueLimit: config.methodQueueLimit,
    });
  }

  async start(): Promise<void> {
    if (config.engineMode === "legacy") return;
    try {
      await this.client.start();
      await this.warmup();
      this.available = true;
    } catch (error) {
      this.available = false;
      console.warn(`Method worker startup failed: ${String(error)}`);
    }
  }

  enqueue(job: ShadowJob): void {
    if (!this.accepting || config.engineMode === "legacy") return;
    if (this.queue.length >= config.methodQueueLimit) {
      void this.recordUnavailable(job, "shadow_queue_full");
      return;
    }
    this.queue.push(job);
    void this.drain();
  }

  status(): Record<string, unknown> {
    return {
      mode: config.engineMode,
      available: this.available,
      queue_depth: this.queue.length,
      pending_requests: this.client.pendingCount,
      profile: config.methodProfile,
      profile_version: config.methodProfileVersion,
      method_version: config.methodVersion,
    };
  }

  async evaluateForEnforcement(request: AuditRequest): Promise<MethodEvaluationResult> {
    const params = await buildRuntimeParams(request);
    return (await this.client.request("evaluate_runtime_trace", params)) as unknown as MethodEvaluationResult;
  }

  persistEnforcementResult(
    request: AuditRequest,
    legacyDecision: AuditDecision,
    result: MethodEvaluationResult,
  ): void {
    void (async () => {
      const prepared = await prepareShadowEvaluation(request);
      await completeMethodEvaluation(
        prepared.evaluationId,
        result,
        classifyMethodDiff(legacyDecision.decision, result.runtime_suggestion),
      );
    })().catch((error: unknown) => console.warn(`Could not persist enforce evaluation: ${String(error)}`));
  }

  async stop(): Promise<void> {
    this.accepting = false;
    const deadline = Date.now() + 2_000;
    while ((this.running || this.queue.length > 0) && Date.now() < deadline) {
      await new Promise((resolveWait) => setTimeout(resolveWait, 20));
    }
    await this.client.stop();
  }

  private async drain(): Promise<void> {
    if (this.running) return;
    this.running = true;
    try {
      while (this.queue.length > 0) {
        const job = this.queue.shift();
        if (job) await this.evaluate(job);
      }
    } finally {
      this.running = false;
    }
  }

  private async evaluate(job: ShadowJob): Promise<void> {
    let evaluationId: string | undefined;
    try {
      const prepared = await prepareShadowEvaluation(job.request, job.revision ?? 1);
      evaluationId = prepared.evaluationId;
      auditEventStream.publish("method_evaluation_queued", { evaluation_id: evaluationId, run_id: job.request.run_id });
      await markMethodRunning(evaluationId);
      const raw = await this.client.request("evaluate_runtime_trace", prepared.params);
      const result = raw as unknown as MethodEvaluationResult;
      await completeMethodEvaluation(
        evaluationId,
        result,
        classifyMethodDiff(job.legacyDecision.decision, result.runtime_suggestion),
      );
      this.available = true;
      auditEventStream.publish("method_evaluation_completed", {
        evaluation_id: evaluationId,
        run_id: job.request.run_id,
        runtime_suggestion: result.runtime_suggestion,
      });
    } catch (error) {
      this.available = false;
      if (evaluationId) {
        const status = error instanceof MethodEngineTimeoutError ? "timeout" : "error";
        await failMethodEvaluation(evaluationId, status, error instanceof Error ? error.name : "error", String(error));
      }
      auditEventStream.publish("method_evaluation_failed", {
        evaluation_id: evaluationId ?? null,
        run_id: job.request.run_id,
        error: String(error),
      });
    }
  }

  private async recordUnavailable(job: ShadowJob, reason: string): Promise<void> {
    try {
      const prepared = await prepareShadowEvaluation(job.request);
      await failMethodEvaluation(prepared.evaluationId, "unavailable", reason, "Shadow queue is unavailable");
    } catch (error) {
      console.warn(`Could not persist unavailable method evaluation: ${String(error)}`);
    }
  }

  async detectObservation(input: {
    run_id: string;
    tool_call_id: string;
    step_seq: number;
    observation: unknown;
    observation_hash?: string;
  }): Promise<Record<string, unknown>> {
    const result = await this.client.request("detect_observation", { observation: input.observation }, 2_000);
    await recordObservationDetection(input.tool_call_id, {
      injection_detected: result.injection_detected === true,
      injection_score: typeof result.injection_score === "number" ? result.injection_score : 0,
      injection_reasons: Array.isArray(result.injection_reasons) ? result.injection_reasons.map(String) : [],
      observation_hash: input.observation_hash ?? null,
    });
    void this.reevaluateAfterObservation(input.run_id, input.step_seq);
    return result;
  }

  private async reevaluateAfterObservation(runId: string, stepSeq: number): Promise<void> {
    const result = await pool.query<{
      request_id: string;
      tool_call_id: string;
      session_id: string;
      run_id: string;
      trace_id: string;
      step_seq: number;
      tool_name: string;
      tool_kind: string;
      param_summary: Record<string, unknown>;
      resource_hint: string | null;
      risk_hint: string | null;
      decision: AuditDecision["decision"];
      risk_level: AuditDecision["risk_level"];
      reason: string;
      matched_rules: string[];
    }>(
      `SELECT tc.request_id, tc.tool_call_id, tc.session_id, tc.run_id, tc.trace_id, tc.step_seq,
              tc.tool_name, tc.tool_kind, tc.param_summary, tc.resource_hint, tc.risk_hint,
              ad.decision, ad.risk_level, ad.reason, ad.matched_rules
         FROM tool_calls tc JOIN audit_decisions ad USING (tool_call_id)
        WHERE tc.run_id=$1 AND tc.step_seq>$2 ORDER BY tc.step_seq`,
      [runId, stepSeq],
    );
    for (const row of result.rows) {
      if (!row.request_id) continue;
      const revision = await nextMethodEvaluationRevision(row.request_id);
      this.enqueue({
        request: {
          request_id: row.request_id,
          schema_version: "v1",
          session_id: row.session_id,
          run_id: row.run_id,
          trace_id: row.trace_id,
          tool_call_id: row.tool_call_id,
          step_seq: row.step_seq,
          semantic_schema_version: "v1",
          tool_name: row.tool_name,
          tool_kind: row.tool_kind,
          raw_params: row.param_summary,
          param_summary: row.param_summary,
          ...(row.resource_hint ? { resource_hint: row.resource_hint } : {}),
          ...(row.risk_hint ? { risk_hint: row.risk_hint } : {}),
          context: {},
        },
        legacyDecision: {
          decision: row.decision,
          risk_level: row.risk_level,
          reason: row.reason,
          matched_rules: row.matched_rules,
        },
        revision,
      });
    }
  }

  private async warmup(): Promise<void> {
    await this.client.request(
      "evaluate_runtime_trace",
      {
        session_id: "warmup",
        run_id: "warmup",
        trace_id: "warmup",
        current_step_seq: 1,
        profile: config.methodProfile,
        profile_version: config.methodProfileVersion,
        method_version: config.methodVersion,
        semantic_schema_version: "v1",
        intent_frame: { task_goal: "warmup", allowed_actions: ["read_file"] },
        events: [{ step_id: 1, tool_name: "read_file", tool_kind: "file_read", args: {}, status: "pending" }],
        trace_completeness: "complete",
      },
      3_000,
    );
  }
}

export const methodShadowService = new MethodShadowService();
