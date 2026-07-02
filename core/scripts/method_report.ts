import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pool, closePool } from "../src/db/pool.js";

const summary = await pool.query(
  `SELECT COUNT(*)::int AS total,
          COUNT(*) FILTER (WHERE status='ok')::int AS ok,
          COUNT(*) FILTER (WHERE status='timeout')::int AS timeout,
          COUNT(*) FILTER (WHERE status='error')::int AS error,
          COUNT(*) FILTER (WHERE status='unavailable')::int AS unavailable,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
          percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
          percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99
     FROM method_evaluations`,
);
const [diffs, violations, completeness, tools] = await Promise.all([
  pool.query("SELECT COALESCE(diff_type,'none') AS key, COUNT(*)::int AS count FROM method_evaluations GROUP BY 1 ORDER BY 2 DESC"),
  pool.query("SELECT violation_type AS key, COUNT(*)::int AS count FROM method_violations GROUP BY 1 ORDER BY 2 DESC"),
  pool.query("SELECT COALESCE(trace_completeness,'unknown') AS key, COUNT(*)::int AS count FROM method_evaluations GROUP BY 1 ORDER BY 2 DESC"),
  pool.query("SELECT tool_kind AS key, COUNT(*)::int AS count FROM tool_calls GROUP BY 1 ORDER BY 2 DESC"),
]);
const report = {
  generated_at: new Date().toISOString(),
  summary: summary.rows[0],
  diff_types: diffs.rows,
  violation_types: violations.rows,
  trace_completeness: completeness.rows,
  tool_kinds: tools.rows,
};
const reportDir = resolve("../doc/core-v2-runtime-method");
await mkdir(reportDir, { recursive: true });
await writeFile(resolve(reportDir, "phase7-shadow-statistics.json"), `${JSON.stringify(report, null, 2)}\n`);
await writeFile(
  resolve(reportDir, "phase7-shadow-statistics.md"),
  `# Phase 7 Shadow Statistics\n\n\`\`\`json\n${JSON.stringify(report, null, 2)}\n\`\`\`\n`,
);
console.log(JSON.stringify(report));
await closePool();

