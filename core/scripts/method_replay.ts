import { readdir, readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, relative } from "node:path";
import { MethodEngineClient } from "../src/engine/methodEngineClient.js";

interface Fixture {
  name: string;
  expected: string;
  params: Record<string, unknown>;
}

const fixtureRoot = resolve("method-engine/fixtures/runtime");
const reportDir = resolve("../doc/core-v2-runtime-method");
const files = await listJson(fixtureRoot);
const fixtures = await Promise.all(
  files.map(async (file) => JSON.parse(await readFile(file, "utf8")) as Fixture),
);
const client = new MethodEngineClient({ timeoutMs: 1_000, queueLimit: 512 });
const latencies: number[] = [];
const results: Array<Record<string, unknown>> = [];
let failures = 0;

try {
  await client.start();
  for (let index = 0; index < 10; index += 1) await client.health();
  for (const fixture of fixtures) {
    let latest: Record<string, unknown> = {};
    for (let iteration = 0; iteration < 20; iteration += 1) {
      const started = performance.now();
      latest = await client.request("evaluate_runtime_trace", fixture.params, 1_000);
      latencies.push(performance.now() - started);
    }
    const actual = String(latest.runtime_suggestion);
    const currentViolations = Array.isArray(latest.current_step_violations)
      ? latest.current_step_violations
      : [];
    const currentStep = Number(fixture.params.current_step_seq);
    const blockHasCurrentEvidence =
      actual !== "BLOCK" ||
      currentViolations.some((violation) => {
        const evidence = (violation as Record<string, unknown>).evidence_steps;
        return Array.isArray(evidence) && evidence.includes(currentStep);
      });
    const passed = actual === fixture.expected && blockHasCurrentEvidence;
    if (!passed) failures += 1;
    results.push({
      fixture: relative(fixtureRoot, files[fixtures.indexOf(fixture)] ?? ""),
      name: fixture.name,
      expected: fixture.expected,
      actual,
      passed,
      current_violation_count: currentViolations.length,
      block_has_current_evidence: blockHasCurrentEvidence,
      mapping: latest.mapping,
      trace_completeness: fixture.params.trace_completeness,
    });
  }
} finally {
  await client.stop();
}

latencies.sort((a, b) => a - b);
const report = {
  generated_at: new Date().toISOString(),
  fixture_count: fixtures.length,
  request_count: latencies.length,
  passed: fixtures.length - failures,
  failed: failures,
  availability: 1,
  timeout_rate: 0,
  error_rate: 0,
  latency_ms: {
    p50: percentile(latencies, 0.5),
    p95: percentile(latencies, 0.95),
    p99: percentile(latencies, 0.99),
  },
  results,
};

await mkdir(reportDir, { recursive: true });
await writeFile(resolve(reportDir, "phase7-replay-report.json"), `${JSON.stringify(report, null, 2)}\n`);
await writeFile(
  resolve(reportDir, "phase7-replay-report.md"),
  [
    "# Phase 7 Runtime Replay Report",
    "",
    `- Fixtures: ${report.fixture_count}`,
    `- Requests: ${report.request_count}`,
    `- Passed: ${report.passed}`,
    `- Failed: ${report.failed}`,
    `- Availability: ${(report.availability * 100).toFixed(3)}%`,
    `- Timeout rate: ${(report.timeout_rate * 100).toFixed(3)}%`,
    `- p50/p95/p99: ${report.latency_ms.p50.toFixed(2)} / ${report.latency_ms.p95.toFixed(2)} / ${report.latency_ms.p99.toFixed(2)} ms`,
    "",
    "| Scenario | Expected | Actual | Current Evidence | Result |",
    "| --- | --- | --- | --- | --- |",
    ...results.map((item) =>
      `| ${item.name} | ${item.expected} | ${item.actual} | ${item.block_has_current_evidence ? "yes" : "no"} | ${item.passed ? "PASS" : "FAIL"} |`,
    ),
    "",
  ].join("\n"),
);

console.log(JSON.stringify(report));
if (failures > 0) process.exitCode = 1;

async function listJson(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) =>
      entry.isDirectory()
        ? listJson(resolve(directory, entry.name))
        : Promise.resolve(entry.name.endsWith(".json") ? [resolve(directory, entry.name)] : []),
    ),
  );
  return nested.flat().sort();
}

function percentile(values: number[], quantile: number): number {
  return values[Math.min(values.length - 1, Math.floor(values.length * quantile))] ?? 0;
}

