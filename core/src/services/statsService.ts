import { pool } from "../db/pool.js";
import type { RuntimeStatus } from "../types/db.js";

interface RuntimeStatusRow {
  tool_calls_24h: string;
  blocked_24h: string;
  high_risk_24h: string;
  policy_hits_24h: string;
}

export async function getRuntimeStatus(): Promise<RuntimeStatus> {
  const result = await pool.query<RuntimeStatusRow>(`
    SELECT
      (SELECT COUNT(*)::text FROM tool_calls
        WHERE started_at >= NOW() - INTERVAL '24 hours') AS tool_calls_24h,
      (SELECT COUNT(*)::text FROM audit_decisions
        WHERE decision = 'BLOCK' AND created_at >= NOW() - INTERVAL '24 hours') AS blocked_24h,
      (SELECT COUNT(*)::text FROM audit_decisions
        WHERE risk_level IN ('high', 'critical')
          AND created_at >= NOW() - INTERVAL '24 hours') AS high_risk_24h,
      (SELECT COUNT(*)::text FROM audit_rule_hits
        WHERE created_at >= NOW() - INTERVAL '24 hours') AS policy_hits_24h
  `);
  const row = result.rows[0];

  return {
    tool_calls_24h: Number(row?.tool_calls_24h ?? 0),
    blocked_24h: Number(row?.blocked_24h ?? 0),
    high_risk_24h: Number(row?.high_risk_24h ?? 0),
    policy_hits_24h: Number(row?.policy_hits_24h ?? 0),
  };
}
