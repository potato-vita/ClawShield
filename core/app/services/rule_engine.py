import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Policy


@dataclass
class RuleResult:
    decision: str
    risk_level: str
    risk_score: float
    reason: str
    matched_rules: list[str]
    event_type: str
    event_title: str
    evidence: list[dict[str, str | None]] = field(default_factory=list)


ACTION_RISK = {
    "ALLOW": ("low", 5.0),
    "WARN": ("medium", 50.0),
    "ASK": ("high", 75.0),
    "BLOCK": ("critical", 95.0),
}


class RuleEngine:
    def evaluate(self, db: Session, request) -> RuleResult:  # type: ignore[no-untyped-def]
        params = request.raw_params or request.params
        text = json.dumps(params, ensure_ascii=False).lower()
        resource = (request.resource_hint or "").lower()
        combined = f"{text} {resource}"

        policy_result = self._evaluate_policies(db, request, params)
        if policy_result:
            return policy_result

        if "rm -rf" in combined:
            return self._result("BLOCK", "critical", 99, "检测到危险递归删除命令。", "dangerous_rm_rf", "dangerous_command", "阻止危险递归删除命令", "dangerous_command", "cmd", "rm -rf")
        if "id_rsa" in combined:
            return self._result("BLOCK", "critical", 98, "工具调用尝试访问 SSH 私钥。", "private_key_access", "sensitive_file_access", "阻止读取 SSH 私钥", "sensitive_path", "path", "id_rsa")
        if ".env" in combined:
            return self._result("BLOCK", "critical", 95, "工具调用尝试读取敏感环境变量文件。", "secret_file_read", "sensitive_file_access", "阻止读取敏感文件 .env", "sensitive_path", "path", ".env")
        if "external-upload.com" in combined:
            return self._result("ASK", "high", 80, "检测到向外部上传站点发送数据。", "external_upload", "external_upload", "外部上传需要审批", "external_sink", "url", "external-upload.com")
        if request.tool_kind == "network_request":
            host = self._host_from(params, request.resource_hint)
            if host not in {"", "localhost", "127.0.0.1"}:
                return self._result("ASK", "high", 75, "未知外部网络目标需要人工审批。", "unknown_external_network", "external_network", "外部网络访问需要审批", "external_sink", "url", host)
        if request.tool_kind == "file_read" and "readme.md" in combined:
            return self._result("ALLOW", "low", 5, "普通只读文件访问。", "readonly_allow", "readonly_access", "允许读取 README", "resource", "path", "README.md")
        if request.tool_kind == "unknown":
            return self._result("WARN", "medium", 50, "未知工具类型，允许执行但记录告警。", "unknown_tool_warn", "unknown_tool", "未知工具调用", "tool_kind", "tool_kind", request.tool_kind)
        return self._result("ALLOW", "low", 10, "未命中风险规则。", "default_allow", "normal_operation", "正常工具调用", "tool_kind", "tool_kind", request.tool_kind)

    def _evaluate_policies(self, db: Session, request, params: dict[str, Any]) -> RuleResult | None:  # type: ignore[no-untyped-def]
        policies = db.scalars(select(Policy).where(Policy.enabled.is_(True)).order_by(Policy.priority.desc())).all()
        for policy in policies:
            condition = json.loads(policy.condition_json)
            field = str(condition.get("field", ""))
            operator = condition.get("operator")
            expected = str(condition.get("value", "")).lower()
            actual = str(params.get(field, request.resource_hint or "")).lower()
            if operator == "contains" and expected and expected in actual:
                action = policy.action.upper()
                risk, score = ACTION_RISK.get(action, ACTION_RISK["WARN"])
                return self._result(action, risk, score, f"命中动态策略：{policy.name}", policy.id, "policy_match", policy.name, "policy", field, expected)
        return None

    @staticmethod
    def _host_from(params: dict[str, Any], hint: str | None) -> str:
        value = str(params.get("url") or hint or "")
        return (urlparse(value).hostname or "").lower()

    @staticmethod
    def _result(decision: str, risk: str, score: float, reason: str, rule: str, event_type: str, title: str, evidence_type: str, key: str, value: str) -> RuleResult:
        return RuleResult(
            decision=decision,
            risk_level=risk,
            risk_score=score,
            reason=reason,
            matched_rules=[rule],
            event_type=event_type,
            event_title=title,
            evidence=[{"type": evidence_type, "key": key, "value": value, "description": reason}],
        )
