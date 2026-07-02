import type { PoolClient } from "pg";

export async function completeRun(
  client: PoolClient,
  runId: string,
  endedAt: Date,
  reason = "agent_end",
): Promise<void> {
  await client.query(
    `UPDATE audit_runs
        SET status = 'completed', ended_at = $2, end_reason = $3,
            last_seen_at = GREATEST(last_seen_at, $2)
      WHERE run_id = $1 AND status = 'active'`,
    [runId, endedAt, reason],
  );
}

