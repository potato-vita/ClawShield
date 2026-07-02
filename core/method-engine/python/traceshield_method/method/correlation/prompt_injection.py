from typing import List

from traceshield_method.method.schemas import SemanticEvent, Violation
from traceshield_method.method.state import TraceState


DANGEROUS_INJECTION_ACTIONS = {
    "network_post",
    "external_send",
    "send_email",
    "shell_exec",
    "delete_file",
    "web_submit",
    "create_calendar_event",
    "modify_calendar_event",
    "modify_financial_transaction",
    "write_user_data",
    "modify_credentials",
}


def check_prompt_injection_drift(state: TraceState, event: SemanticEvent) -> List[Violation]:
    if not state.untrusted_injection_steps:
        return []
    if event.risk_level == "high" or event.semantic_action in DANGEROUS_INJECTION_ACTIONS:
        return [
            Violation(
                violation_type="prompt_injection_induced_drift",
                evidence_steps=[state.untrusted_injection_steps[-1], event.step_id],
                target=event.target_resource,
                source="prompt_injection",
                reason="前序工具返回内容包含疑似注入指令，后续执行了高风险动作。",
            )
        ]
    return []
