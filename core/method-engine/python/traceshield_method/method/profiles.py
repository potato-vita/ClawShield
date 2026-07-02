from traceshield_method.method.evaluator import EvaluationSwitches


PROFILE_DESCRIPTIONS = {
    "strict": "Strict TraceShield security audit. High-risk injected behavior is blocked even when benchmark labels only count fully successful injection goals.",
    "agentdojo_official": "AgentDojo official-label profile. Keeps capability/resource checks but disables broad chain and prompt-injection blocking to better match task-specific security labels.",
    "boundary_only": "Capability/resource/trust-boundary checks only. Disables semantic relation, transition, and risk-graph analysis.",
}


def switches_for_profile(profile: str) -> EvaluationSwitches:
    if profile == "strict":
        return EvaluationSwitches()
    if profile == "agentdojo_official":
        return EvaluationSwitches(
            semantic_relation=False,
            step_transition=False,
            prompt_injection=False,
            sensitive_external_chain=False,
            risk_graph_analysis=False,
            destructive_after_read=False,
        )
    if profile == "boundary_only":
        return EvaluationSwitches(
            semantic_relation=False,
            step_transition=False,
            prompt_injection=True,
            sensitive_external_chain=False,
            risk_graph_analysis=False,
            destructive_after_read=False,
        )
    raise ValueError(f"Unknown profile: {profile}")
