# Round 11 - Real OpenClaw Visible Tool

Time: 2026-06-17 14:19 CST

## Goal

Make the installed TraceShield OpenClaw plugin visible from a real OpenClaw agent turn, not only active as a background security hook.

## Findings

- `traceshield-security-plugin` was already installed and loaded in the real OpenClaw plugin registry.
- The earlier OpenClaw chat answer saying there were no user-installed third-party plugins was misleading because it was answering from the model-visible skill/tool surface, not from the native plugin registry.
- The security hook was already active and had blocked a real dangerous command attempt through `before_tool_call`.
- The status tool existed in the plugin contract but was not available to the model until OpenClaw's tool policy allowed it.

## Change Applied To Real OpenClaw Config

Added the TraceShield status tool to OpenClaw's global tool allow additions:

```bash
printf '%s\n' '{"tools":{"alsoAllow":["traceshield_status"]}}' | openclaw config patch --stdin
systemctl --user restart openclaw-gateway.service
```

Effective config:

```json
{
  "profile": "coding",
  "alsoAllow": [
    "traceshield_status"
  ]
}
```

## Verification

Command:

```bash
openclaw agent \
  --session-key agent:main:traceshield-status-visible-2 \
  --message '请调用 traceshield_status 工具查看 TraceShield 状态，然后只把工具返回内容原样告诉我。' \
  --timeout 120 \
  --json
```

Observed effect:

- The agent tool catalog included `traceshield_status`.
- The model called `traceshield_status` exactly once.
- The final visible answer was the tool output:

```text
TraceShield Security Plugin is loaded.
Core URL: http://127.0.0.1:8787
Audit timeout: 400ms
Fallback enabled: true
Debug full payload: false
Queued events: 1
```

The JSON result also reported:

```json
{
  "toolSummary": {
    "calls": 1,
    "tools": [
      "traceshield_status"
    ],
    "failures": 0
  }
}
```

## User-Facing Interpretation

TraceShield is now connected in two ways:

1. Background security integration: OpenClaw tool calls pass through the TraceShield `before_tool_call` audit hook.
2. Visible plugin demonstration: real OpenClaw agents can call `traceshield_status` and display the plugin status.

