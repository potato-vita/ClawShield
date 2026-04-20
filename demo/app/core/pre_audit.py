from pathlib import Path

from app.config import get_settings


class PreAuditEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def run(self, target_paths: list[str], skill_source: str | None = None) -> dict:
        findings: list[dict] = []
        score = 100.0

        for raw in target_paths:
            path = Path(raw)
            if not path.exists() or not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for keyword in self.settings.preaudit_keywords:
                if keyword in content:
                    findings.append(
                        {
                            "type": "keyword",
                            "target": str(path),
                            "keyword": keyword,
                            "message": f"Detected risky keyword: {keyword}",
                        }
                    )
                    score -= 8

            if ".env" in content or "SECRET" in content:
                findings.append(
                    {
                        "type": "hardcoded_sensitive_ref",
                        "target": str(path),
                        "message": "Potential sensitive resource hardcoding",
                    }
                )
                score -= 6

        if skill_source and skill_source == "unknown":
            findings.append(
                {
                    "type": "skill_trust",
                    "target": skill_source,
                    "message": "Skill source trust level is unknown",
                }
            )
            score -= 10

        score = max(0.0, score)
        if score >= 85:
            level = "low"
        elif score >= 65:
            level = "medium"
        elif score >= 40:
            level = "high"
        else:
            level = "critical"

        suggestions = [
            "限制高危函数调用并通过 Gateway 统一封装",
            "确保技能来源可信并补充能力声明",
            "避免硬编码敏感路径与密钥字段",
        ]

        return {
            "pre_audit_score": score,
            "result_level": level,
            "risk_items": findings,
            "suggestions": suggestions,
        }
