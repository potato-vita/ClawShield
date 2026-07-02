ALTER TABLE audit_decisions
  ADD COLUMN IF NOT EXISTS engine TEXT,
  ADD COLUMN IF NOT EXISTS engine_version TEXT,
  ADD COLUMN IF NOT EXISTS method_evaluation_id UUID;

