CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audit_sessions (
  session_id TEXT PRIMARY KEY,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  CHECK (last_seen_at >= first_seen_at)
);

CREATE TABLE IF NOT EXISTS audit_runs (
  run_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES audit_sessions(session_id) ON DELETE CASCADE,
  trace_id TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tool_call_count INTEGER NOT NULL DEFAULT 0 CHECK (tool_call_count >= 0),
  blocked_count INTEGER NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
  warn_count INTEGER NOT NULL DEFAULT 0 CHECK (warn_count >= 0),
  ask_count INTEGER NOT NULL DEFAULT 0 CHECK (ask_count >= 0),
  risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  final_decision TEXT NOT NULL DEFAULT 'ALLOW' CHECK (final_decision IN ('ALLOW', 'WARN', 'ASK', 'BLOCK')),
  CHECK (last_seen_at >= started_at)
);

CREATE TABLE IF NOT EXISTS trace_events (
  event_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL CHECK (schema_version = 'v1'),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'message_received', 'llm_input', 'llm_output', 'message_sending',
    'before_tool_call', 'after_tool_call', 'agent_end', 'fallback_decision'
  )),
  occurred_at TIMESTAMPTZ NOT NULL,
  plugin_id TEXT NOT NULL,
  gateway_id TEXT,
  session_id TEXT NOT NULL REFERENCES audit_sessions(session_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  trace_id TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('sync', 'async')),
  raw_payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  message_row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT NOT NULL UNIQUE REFERENCES trace_events(event_id) ON DELETE CASCADE,
  message_id TEXT,
  session_id TEXT NOT NULL REFERENCES audit_sessions(session_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  trace_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'message_received', 'llm_input', 'llm_output', 'message_sending', 'agent_end'
  )),
  role TEXT,
  content_preview TEXT,
  content_hash TEXT,
  summary JSONB,
  metadata JSONB,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_calls (
  tool_call_id TEXT PRIMARY KEY,
  request_id TEXT UNIQUE,
  session_id TEXT NOT NULL REFERENCES audit_sessions(session_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  trace_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  tool_kind TEXT NOT NULL,
  param_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
  resource_hint TEXT,
  risk_hint TEXT,
  raw_params JSONB,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'error', 'unknown')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_results (
  tool_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT NOT NULL UNIQUE REFERENCES trace_events(event_id) ON DELETE CASCADE,
  tool_call_id TEXT NOT NULL REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
  result_preview TEXT,
  result_hash TEXT,
  result_summary JSONB,
  error_data JSONB,
  raw_result JSONB,
  duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_decisions (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL UNIQUE,
  tool_call_id TEXT NOT NULL REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
  decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'WARN', 'ASK', 'BLOCK')),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  reason TEXT NOT NULL,
  matched_rules TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  policy_version TEXT NOT NULL DEFAULT 'v1',
  evidence_refs TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  modified_params JSONB,
  approval JSONB,
  fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  description TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  priority INTEGER NOT NULL DEFAULT 100 CHECK (priority >= 0),
  decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'WARN', 'ASK', 'BLOCK')),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  policy_version TEXT NOT NULL DEFAULT 'v1',
  config JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_rule_hits (
  rule_hit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID NOT NULL REFERENCES audit_decisions(decision_id) ON DELETE CASCADE,
  policy_id TEXT NOT NULL,
  matched BOOLEAN NOT NULL DEFAULT TRUE,
  detail JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (decision_id, policy_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  tool_call_id TEXT REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
  decision_id UUID REFERENCES audit_decisions(decision_id) ON DELETE CASCADE,
  evidence_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_steps (
  evidence_step_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id UUID NOT NULL REFERENCES evidence_items(evidence_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
  tool_call_id TEXT REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
  step_order INTEGER NOT NULL CHECK (step_order >= 0),
  step_type TEXT NOT NULL,
  title TEXT NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (evidence_id, step_order)
);

CREATE INDEX IF NOT EXISTS idx_audit_runs_session_started ON audit_runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_trace_events_run_occurred ON trace_events(run_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_trace_events_type_occurred ON trace_events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_run_occurred ON messages(run_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_run_started ON tool_calls(run_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_started ON tool_calls(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_results_tool_call ON tool_results(tool_call_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_decisions_tool_created ON audit_decisions(tool_call_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_decisions_decision_created ON audit_decisions(decision, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rule_hits_policy_created ON audit_rule_hits(policy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_items_run_created ON evidence_items(run_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_evidence_steps_run_order ON evidence_steps(run_id, created_at ASC, step_order ASC);
