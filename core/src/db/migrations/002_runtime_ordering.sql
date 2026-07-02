ALTER TABLE audit_runs
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS end_reason TEXT;

ALTER TABLE audit_runs DROP CONSTRAINT IF EXISTS audit_runs_status_check;
ALTER TABLE audit_runs ADD CONSTRAINT audit_runs_status_check
  CHECK (status IN ('active', 'completed', 'failed', 'timed_out', 'abandoned'));

ALTER TABLE tool_calls
  ADD COLUMN IF NOT EXISTS step_seq INTEGER,
  ADD COLUMN IF NOT EXISTS correlation_source TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tool_calls_run_step
  ON tool_calls(run_id, step_seq)
  WHERE step_seq IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tool_calls_run_step
  ON tool_calls(run_id, step_seq ASC);

