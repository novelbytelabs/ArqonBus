"""CASIL error and reason codes."""

from dataclasses import dataclass
from typing import Optional


# Policy decision reason codes
CASIL_POLICY_BLOCKED_SECRET = "CASIL_POLICY_BLOCKED_SECRET"
CASIL_POLICY_OVERSIZE = "CASIL_POLICY_OVERSIZE"
CASIL_POLICY_REDACTED = "CASIL_POLICY_REDACTED"
CASIL_POLICY_ALLOWED = "CASIL_POLICY_ALLOWED"
CASIL_INTERNAL_ERROR = "CASIL_INTERNAL_ERROR"
CASIL_OUT_OF_SCOPE = "CASIL_OUT_OF_SCOPE"
CASIL_DISABLED = "CASIL_DISABLED"
CASIL_MONITOR_MODE = "CASIL_MONITOR_MODE"


class CASILException(Exception):
    """Base exception for CASIL errors."""

    def __init__(self, message: str, reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason or CASIL_INTERNAL_ERROR


@dataclass
class CASILReason:
    """Structured reason metadata for CASIL decisions."""

    code: str
    detail: Optional[str] = None

