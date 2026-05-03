from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BehaviorExplanation:
    category: str
    label: str
    explanation: str


def explain_event(
    *,
    event_type: str,
    actor_type: str | None = None,
    tool_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    semantic_decision: str | None = None,
    policy_decision: str | None = None,
    disposition: str | None = None,
    alignment_score: float | None = None,
    intended_effect: str | None = None,
    actual_effect: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
) -> BehaviorExplanation:
    et = (event_type or "").strip()
    actor = (actor_type or "").lower()
    tool = tool_id or "未知工具"
    resource = f"{resource_type or 'unknown'}:{resource_id or 'unknown'}"
    sem = semantic_decision or "unknown"
    pol = policy_decision or "unknown"
    disp = disposition or "unknown"
    effect = actual_effect or intended_effect or "unknown"

    if et == "chat_message_received":
        if actor == "user":
            text = (input_summary or "").strip() or "(无文本)"
            return BehaviorExplanation(
                category="chat",
                label="用户消息",
                explanation=f"用户发来新消息：{text[:60]}",
            )
        text = (output_summary or "").strip() or "(无文本)"
        return BehaviorExplanation(
            category="chat",
            label="助手回复",
            explanation=f"系统记录模型回复：{text[:60]}",
        )

    if et == "tool_call_requested":
        return BehaviorExplanation(
            category="tool",
            label="请求调用工具",
            explanation=f"模型尝试调用工具 {tool}，准备执行任务步骤。",
        )

    if et == "alignment_evaluated":
        score_text = "-" if alignment_score is None else f"{alignment_score:.2f}"
        return BehaviorExplanation(
            category="security",
            label="目标一致性评估",
            explanation=f"一致性={sem}，评分={score_text}，预期影响={intended_effect or 'unknown'}。",
        )

    if et == "policy_check_completed":
        return BehaviorExplanation(
            category="security",
            label="策略检查完成",
            explanation=f"策略决策={pol}，处置建议={disp}。",
        )

    if et == "risk_rule_matched":
        detail = (input_summary or "").strip()
        return BehaviorExplanation(
            category="risk",
            label="命中风险规则",
            explanation=detail or "触发了一条风险规则。",
        )

    if et == "disposition_applied":
        return BehaviorExplanation(
            category="security",
            label="应用处置动作",
            explanation=f"系统执行处置={disp}，用于限制风险扩散。",
        )

    if et == "resource_access_requested":
        return BehaviorExplanation(
            category="tool",
            label="请求访问资源",
            explanation=f"工具访问资源 {resource}，预期/实际影响={effect}。",
        )

    if et == "tool_execution_started":
        return BehaviorExplanation(
            category="tool",
            label="开始执行工具",
            explanation=f"工具 {tool} 开始执行。",
        )

    if et == "tool_execution_completed":
        return BehaviorExplanation(
            category="tool",
            label="完成执行工具",
            explanation=f"工具 {tool} 已完成，实际影响={effect}。",
        )

    if et == "tool_result_received":
        return BehaviorExplanation(
            category="tool",
            label="收到工具结果",
            explanation=f"系统收到 {tool} 的执行结果，状态已记录。",
        )

    if et == "task_step_initialized":
        return BehaviorExplanation(
            category="system",
            label="初始化任务步骤",
            explanation=f"建立初始步骤：{(output_summary or input_summary or '').strip()[:60]}",
        )

    if et == "task_step_transitioned":
        return BehaviorExplanation(
            category="system",
            label="任务步骤迁移",
            explanation=f"步骤从 {(input_summary or '').strip()[:30]} 迁移到 {(output_summary or '').strip()[:30]}。",
        )

    if et == "goal_contract_created":
        return BehaviorExplanation(
            category="system",
            label="创建目标契约",
            explanation=f"任务目标已结构化，意图={(input_summary or 'unknown')}。",
        )

    if et == "task_received":
        return BehaviorExplanation(
            category="system",
            label="接收任务",
            explanation="系统收到一条新任务，准备创建运行上下文。",
        )

    return BehaviorExplanation(
        category="system",
        label=et or "事件",
        explanation="系统记录了一条运行事件。",
    )
