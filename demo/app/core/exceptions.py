class ClawShieldError(Exception):
    """Base error for ClawShield."""


class GatewayBlockedError(ClawShieldError):
    """Raised when an action is blocked by policy."""


class WorkspaceViolationError(ClawShieldError):
    """Raised when a path escapes allowed workspace."""
