from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    ALERT = "alert"
    BLOCK = "block"


class GatewayStatus(str, Enum):
    ALLOWED = "allowed"
    ALERTED = "alerted"
    BLOCKED = "blocked"
    ERROR = "error"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
