# Presentation Points (PPT / Defense Ready)

## 1) 我们解决什么问题

ClawShield addresses the governance gap in tool-calling AI agents:

- not only "can it call a tool"
- but "should it call this tool on this resource in this task context"
- and "how do we produce auditable evidence for the decision"

## 2) 为什么 Guardrails 不等于整个系统

Guardrails is semantic judgment for candidate actions.  
It does not replace runtime enforcement, resource-level policy checks, and evidence persistence.

ClawShield extends it with:

- policy evaluation on task/tool/resource triples
- unified gateway execution point
- normalized event stream and post-run evidence chain

## 3) 为什么需要统一安全网关

Without a unified gateway, interception and enforcement logic are fragmented by tool type.

Gateway value:

- single enforcement entry for all action types
- same disposition contract (`allow/warn/deny`)
- consistent telemetry for risk replay and debugging

## 4) 为什么强调 run 级证据链

Single events are weak signals; meaningful risk is often chained.

Run-level evidence chain provides:

- ordered timeline
- graph relationships between task, tools, resources, and findings
- deterministic final conclusion for demo and review

## 5) 三个标准案例分别说明了什么

1. `workspace_escape`: demonstrates boundary escape prevention.
2. `env_then_http`: demonstrates sensitive-data exfiltration sequence detection.
3. `analysis_high_risk_tool`: demonstrates context-aware tool-risk governance.
