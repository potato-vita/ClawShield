import "dotenv/config";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Client } from "pg";

const databaseUrl = process.env.TRACESHIELD_DATABASE_URL;
if (!databaseUrl) {
  throw new Error("TRACESHIELD_DATABASE_URL is required (copy .env.example to .env)");
}

const here = dirname(fileURLToPath(import.meta.url));
const [schema, seedPolicies] = await Promise.all([
  readFile(join(here, "schema.sql"), "utf8"),
  readFile(join(here, "seed_policies.sql"), "utf8"),
]);

const client = new Client({ connectionString: databaseUrl });
await client.connect();

try {
  await client.query("BEGIN");
  await client.query(schema);
  await client.query(seedPolicies);
  await client.query("COMMIT");
  console.log("TraceShield database migration completed.");
} catch (error) {
  await client.query("ROLLBACK");
  throw error;
} finally {
  await client.end();
}
