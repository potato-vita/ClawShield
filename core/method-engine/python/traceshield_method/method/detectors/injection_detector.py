import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, List, Optional


LEETSPEAK_TABLE = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }
)

HIGH_CONFIDENCE_PATTERNS = [
    r"\b(ignore|disregard|bypass|override)\b.{0,48}\b(previous|prior|earlier|above|system|developer)\b.{0,32}\b(\w{0,3}nstruction|message|rule|policy|prompt)s?\b",
    r"\b(reveal|print|show|dump|leak|exfiltrate)\b.{0,48}\b(secret|credential|token|api[_ -]?key|password|system prompt|developer message)\b",
    r"\b(read|open|copy|send|upload)\b.{0,48}\b(\.env|id_rsa|credential|token|api[_ -]?key|password|secret)\b",
    r"\b(delete|erase|remove)\b.{0,32}\b(log|audit|trace|evidence)s?\b",
    r"\b(send|forward|upload|post)\b.{0,48}\b(to|at)\b.{0,48}\b(attacker|evil|webhook|external|gmail|email)\b",
    r"忽略.{0,20}(之前|以上|系统|开发者).{0,20}(指令|规则|提示)",
    r"(泄露|发送|上传|读取).{0,24}(密钥|令牌|密码|凭据|系统提示|\.env)",
]

MEDIUM_CONFIDENCE_PATTERNS = [
    r"\btodo\s*:",
    r"\bimportant (message|instruction|notice)s?\b",
    r"\bbefore you can solve\b",
    r"\bplease do the following first\b",
    r"\byou should use the tool\b",
    r"<information>",
    r"```(?:system|developer|assistant|tool)?",
    r"<!--.*?(ignore|send|upload|secret).*?-->",
    r"(请|务必|必须).{0,16}(先|改为|转而).{0,24}(发送|上传|删除|读取)",
]


@dataclass(frozen=True)
class InjectionDetection:
    is_injection: bool
    score: float
    reasons: List[str] = field(default_factory=list)
    normalized_text: str = ""


def detect_prompt_injection(
    text: Optional[str],
    extra_keywords: Optional[Iterable[str]] = None,
) -> InjectionDetection:
    if not text:
        return InjectionDetection(False, 0.0, [], "")

    normalized = normalize_text(text)
    reasons: List[str] = []
    score = 0.0

    for pattern in HIGH_CONFIDENCE_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL):
            reasons.append(f"high:{pattern}")
            score += 0.6

    for pattern in MEDIUM_CONFIDENCE_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE | re.DOTALL):
            reasons.append(f"medium:{pattern}")
            score += 0.3

    for keyword in extra_keywords or []:
        keyword_text = normalize_text(str(keyword))
        if keyword_text and keyword_text in normalized:
            reasons.append(f"keyword:{keyword}")
            score += 0.25

    capped_score = min(score, 1.0)
    return InjectionDetection(capped_score >= 0.5, capped_score, reasons, normalized)


def contains_prompt_injection(text: Optional[str], extra_keywords: Optional[Iterable[str]] = None) -> bool:
    return detect_prompt_injection(text, extra_keywords).is_injection


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.translate(LEETSPEAK_TABLE)
    normalized = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", normalized)
    normalized = re.sub(r"[\s_\\/\-]+", " ", normalized)
    return normalized.lower()
