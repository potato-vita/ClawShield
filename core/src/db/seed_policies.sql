INSERT INTO policies (
  policy_id, display_name, description, enabled, priority, decision, risk_level, policy_version, config
) VALUES
  (
    'deny_secret_file_read',
    'Deny secret file reads',
    'Blocks file or shell reads targeting common secret files and private keys.',
    TRUE, 10, 'BLOCK', 'critical', 'v1',
    '{"patterns":[".env","id_rsa","id_ed25519","private_key","/etc/shadow"]}'::JSONB
  ),
  (
    'confirm_dangerous_shell_command',
    'Confirm dangerous shell commands',
    'Requires explicit user approval for destructive shell commands such as rm -rf, mkfs and dd if=.',
    TRUE, 20, 'ASK', 'critical', 'v1',
    '{"patterns":["rm -rf","mkfs","dd if="]}'::JSONB
  ),
  (
    'ask_external_network_request',
    'Ask before external network requests',
    'Requires approval before a tool accesses a non-local URL.',
    TRUE, 30, 'ASK', 'medium', 'v1',
    '{"local_hosts":["localhost","127.0.0.1","::1"]}'::JSONB
  ),
  (
    'warn_unknown_tool',
    'Warn on unknown tools',
    'Allows unknown tools with a visible warning and an audit trail.',
    TRUE, 40, 'WARN', 'medium', 'v1',
    '{}'::JSONB
  )
ON CONFLICT (policy_id) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  description = EXCLUDED.description,
  enabled = EXCLUDED.enabled,
  priority = EXCLUDED.priority,
  decision = EXCLUDED.decision,
  risk_level = EXCLUDED.risk_level,
  policy_version = EXCLUDED.policy_version,
  config = EXCLUDED.config,
  updated_at = NOW();

DELETE FROM policies WHERE policy_id = 'deny_dangerous_shell_command';
