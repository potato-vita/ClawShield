import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from traceshield_method.method.schemas import IntentFrame, SemanticEvent, Violation


HIGH_IMPACT_ACTIONS = {
    "network_post",
    "external_send",
    "send_email",
    "shell_exec",
    "delete_file",
    "delete_email",
    "web_submit",
    "write_file",
    "create_calendar_event",
    "modify_calendar_event",
    "modify_financial_transaction",
    "write_user_data",
    "modify_credentials",
}

DEFAULT_ACTION_KEYWORDS = {
    "send_email": {"email", "mail", "message", "notify", "send", "forward", "邮件", "发送", "通知"},
    "external_send": {"send", "transfer", "share", "forward", "pay", "payment", "wire", "发送", "转账", "分享"},
    "network_post": {"post", "upload", "webhook", "api", "submit", "上传", "提交", "外发"},
    "web_submit": {"submit", "form", "apply", "checkout", "提交", "表单"},
    "delete_file": {"delete", "remove", "erase", "clean", "删除", "清理"},
    "delete_email": {"delete", "remove", "erase", "删除", "清理"},
    "write_file": {"write", "create", "append", "save", "update", "写入", "保存", "创建"},
    "read_file": {"read", "open", "inspect", "summarize", "读取", "查看", "总结"},
    "read_database_field": {"query", "database", "patient", "record", "field", "查询", "数据库", "字段"},
    "sql_query": {"query", "sql", "database", "table", "查询", "数据库"},
    "create_calendar_event": {"calendar", "schedule", "meeting", "book", "日历", "会议", "预约"},
    "modify_calendar_event": {"calendar", "reschedule", "cancel", "meeting", "日历", "改期", "取消"},
    "modify_financial_transaction": {"transaction", "payment", "transfer", "bank", "转账", "交易", "银行"},
    "write_user_data": {"profile", "user", "account", "update", "用户", "账户", "更新"},
    "modify_credentials": {"password", "credential", "login", "密码", "凭据", "登录"},
}


@dataclass(frozen=True)
class RelationJudgment:
    relation: str
    confidence: float
    reason: str


def check_semantic_relation(
    intent: IntentFrame,
    event: SemanticEvent,
    security_knowledge: Optional[Dict[str, Any]] = None,
) -> List[Violation]:
    judgment = judge_event_relation(intent, event, security_knowledge)
    if judgment.relation not in {"contradiction", "unrelated"}:
        return []
    if event.risk_level != "high" and event.semantic_action not in HIGH_IMPACT_ACTIONS:
        return []
    return [
        Violation(
            violation_type="intent_tool_inconsistency",
            evidence_steps=[event.step_id],
            target=event.target_resource,
            source="semantic_relation",
            metadata={"relation": judgment.relation, "confidence": judgment.confidence},
            reason=f"语义关系判断认为动作 {event.semantic_action} 与用户目标不一致：{judgment.reason}",
        )
    ]


def judge_event_relation(
    intent: IntentFrame,
    event: SemanticEvent,
    security_knowledge: Optional[Dict[str, Any]] = None,
) -> RelationJudgment:
    action = event.semantic_action
    if action in intent.forbidden_actions:
        return RelationJudgment("contradiction", 1.0, "动作在 forbidden_actions 中。")

    if action not in HIGH_IMPACT_ACTIONS and event.risk_level != "high":
        return RelationJudgment("supported", 0.65, "非高影响动作默认视为辅助步骤。")

    text = f"{_normalize(intent.task_goal)} {_normalize(str(intent.constraints.get('user_query', '')))}".strip()
    keywords = _action_keywords(action, security_knowledge)

    if _explicit_action_supported(text, action, keywords):
        return RelationJudgment("entailed", 0.86, "用户目标中出现了该高影响动作的语义线索。")

    if _target_supported(text, event.target_resource):
        return RelationJudgment("supported", 0.72, "目标资源或收件对象与用户目标存在文本关联。")

    if action in intent.allowed_actions and _has_goal_specific_context(text):
        return RelationJudgment("unrelated", 0.72, "虽然动作在 allowed_actions 中，但用户目标没有支持该高影响动作的语义线索。")

    if action not in intent.allowed_actions:
        return RelationJudgment("contradiction", 0.82, "高影响动作不在 allowed_actions 中。")

    return RelationJudgment("uncertain", 0.5, "没有足够证据判断该动作是否偏离用户目标。")


def _action_keywords(action: str, security_knowledge: Optional[Dict[str, Any]]) -> Set[str]:
    configured = ((security_knowledge or {}).get("semantic_relations", {}) or {}).get("action_keywords", {})
    values = configured.get(action) if isinstance(configured, dict) else None
    if isinstance(values, list):
        return {str(value).lower() for value in values}
    return set(DEFAULT_ACTION_KEYWORDS.get(action, set()))


def _explicit_action_supported(text: str, action: str, keywords: Set[str]) -> bool:
    action_terms = set(action.replace("_", " ").split())
    return any(term and term in text for term in action_terms | keywords)


def _target_supported(text: str, target: Optional[str]) -> bool:
    if not target:
        return False
    tokens = [token for token in re.split(r"[^a-zA-Z0-9@\u4e00-\u9fff.]+", target.lower()) if len(token) >= 4]
    return any(token in text for token in tokens)


def _has_goal_specific_context(text: str) -> bool:
    return len([token for token in re.split(r"\s+", text) if token]) >= 3 or bool(re.search(r"[\u4e00-\u9fff]{4,}", text))


def _normalize(text: str) -> str:
    lowered = text.lower().replace("_", " ")
    return re.sub(r"\s+", " ", lowered).strip()
