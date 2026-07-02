ALTER TABLE audit_runs
  ADD COLUMN IF NOT EXISTS intent_frame JSONB,
  ADD COLUMN IF NOT EXISTS intent_frame_version TEXT,
  ADD COLUMN IF NOT EXISTS intent_source TEXT,
  ADD COLUMN IF NOT EXISTS intent_confidence TEXT,
  ADD COLUMN IF NOT EXISTS audit_profile TEXT,
  ADD COLUMN IF NOT EXISTS method_config_version TEXT;

ALTER TABLE tool_calls
  ADD COLUMN IF NOT EXISTS semantic_tool_type TEXT,
  ADD COLUMN IF NOT EXISTS semantic_action TEXT,
  ADD COLUMN IF NOT EXISTS semantic_risk_level TEXT,
  ADD COLUMN IF NOT EXISTS target_resource TEXT,
  ADD COLUMN IF NOT EXISTS mapping_source TEXT,
  ADD COLUMN IF NOT EXISTS mapping_confidence NUMERIC;

ALTER TABLE tool_results
  ADD COLUMN IF NOT EXISTS injection_detected BOOLEAN,
  ADD COLUMN IF NOT EXISTS injection_score NUMERIC,
  ADD COLUMN IF NOT EXISTS injection_reasons JSONB,
  ADD COLUMN IF NOT EXISTS observation_hash TEXT,
  ADD COLUMN IF NOT EXISTS trace_completeness TEXT;

CREATE TABLE IF NOT EXISTS method_evaluations (
  method_evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  tool_call_id TEXT NOT NULL REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  step_seq INTEGER,
  profile TEXT NOT NULL,
  profile_version TEXT NOT NULL,
  method_version TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'ok', 'timeout', 'error', 'unavailable')),
  method_decision TEXT,
  runtime_suggestion TEXT CHECK (runtime_suggestion IS NULL OR runtime_suggestion IN ('ALLOW', 'WARN', 'ASK', 'BLOCK')),
  risk_level TEXT,
  latency_ms NUMERIC,
  diff_type TEXT,
  trace_completeness TEXT,
  input_hash TEXT,
  error_code TEXT,
  error_message TEXT,
  evaluation_revision INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  UNIQUE (request_id, profile, method_version, evaluation_revision)
);

CREATE TABLE IF NOT EXISTS method_violations (
  method_violation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  method_evaluation_id UUID NOT NULL REFERENCES method_evaluations(method_evaluation_id) ON DELETE CASCADE,
  violation_type TEXT NOT NULL,
  source TEXT,
  reason TEXT NOT NULL,
  target TEXT,
  evidence_steps JSONB NOT NULL DEFAULT '[]'::JSONB,
  is_current_step BOOLEAN NOT NULL DEFAULT FALSE,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS method_graph_snapshots (
  method_graph_snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  method_evaluation_id UUID NOT NULL UNIQUE REFERENCES method_evaluations(method_evaluation_id) ON DELETE CASCADE,
  nodes JSONB NOT NULL DEFAULT '[]'::JSONB,
  edges JSONB NOT NULL DEFAULT '[]'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_method_evaluations_run_created ON method_evaluations(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_method_evaluations_status_created ON method_evaluations(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_method_violations_eval ON method_violations(method_evaluation_id);

