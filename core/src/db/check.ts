import "dotenv/config";
import { Client } from "pg";

const expectedTables = [
  "audit_sessions",
  "audit_runs",
  "trace_events",
  "messages",
  "tool_calls",
  "tool_results",
  "audit_decisions",
  "audit_rule_hits",
  "policies",
  "evidence_items",
  "evidence_steps",
  "method_evaluations",
  "method_violations",
  "method_graph_snapshots",
] as const;

const databaseUrl = process.env.TRACESHIELD_DATABASE_URL;
if (!databaseUrl) {
  throw new Error("TRACESHIELD_DATABASE_URL is required (copy .env.example to .env)");
}

const client = new Client({ connectionString: databaseUrl });
await client.connect();

try {
  const timeResult = await client.query<{ database_time: Date }>("SELECT NOW() AS database_time");
  const tableResult = await client.query<{ table_name: string }>(
    `SELECT table_name
       FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name = ANY($1::text[])
      ORDER BY table_name`,
    [expectedTables],
  );
  const policyResult = await client.query<{ count: string }>("SELECT COUNT(*)::text AS count FROM policies");

  const found = new Set(tableResult.rows.map((row) => row.table_name));
  const missing = expectedTables.filter((table) => !found.has(table));
  const policyCount = Number(policyResult.rows[0]?.count ?? 0);

  console.log(`database_time=${timeResult.rows[0]?.database_time.toISOString()}`);
  console.log(`tables=${found.size}/${expectedTables.length}`);
  console.log(`policies=${policyCount}`);

  if (missing.length > 0) {
    throw new Error(`Missing tables: ${missing.join(", ")}`);
  }
  if (policyCount < 4) {
    throw new Error(`Expected at least 4 policies, found ${policyCount}`);
  }

  console.log("TraceShield database check passed.");
} finally {
  await client.end();
}
