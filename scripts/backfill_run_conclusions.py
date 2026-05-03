#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "clawshield.db"

RISK_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
    "severe": 4,
}
DISPOSITION_RANK = {
    "allow": 1,
    "degrade": 2,
    "warn": 2,
    "deny": 3,
    "block": 3,
}


def _merge_risk(current: str | None, incoming: str | None) -> str | None:
    a = (current or "").strip().lower()
    b = (incoming or "").strip().lower()
    if RISK_RANK.get(b, 0) > RISK_RANK.get(a, 0):
        return b
    return a or None


def _merge_disposition(current: str | None, incoming: str | None) -> str | None:
    a = (current or "").strip().lower()
    b = (incoming or "").strip().lower()
    if b == "block":
        b = "deny"
    if a == "block":
        a = "deny"
    if DISPOSITION_RANK.get(b, 0) > DISPOSITION_RANK.get(a, 0):
        return b
    return a or None


def main() -> int:
    if not DB_PATH.exists():
        print(f"db not found: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    runs = cur.execute("select run_id, final_risk_level, disposition from runs").fetchall()
    updated = 0
    unchanged = 0

    for run in runs:
        run_id = str(run["run_id"])
        risk = run["final_risk_level"]
        disposition = run["disposition"]

        rows = cur.execute(
            """
            select risk_level, disposition
            from audit_events
            where run_id = ?
            and (risk_level is not null or disposition is not null)
            """,
            (run_id,),
        ).fetchall()

        merged_risk = risk
        merged_disposition = disposition
        for item in rows:
            merged_risk = _merge_risk(merged_risk, item["risk_level"])
            merged_disposition = _merge_disposition(merged_disposition, item["disposition"])

        if merged_risk != risk or merged_disposition != disposition:
            cur.execute(
                "update runs set final_risk_level = ?, disposition = ? where run_id = ?",
                (merged_risk, merged_disposition, run_id),
            )
            updated += 1
        else:
            unchanged += 1

    conn.commit()
    conn.close()
    print(
        f"backfill done: total_runs={len(runs)} updated={updated} unchanged={unchanged} db={DB_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
