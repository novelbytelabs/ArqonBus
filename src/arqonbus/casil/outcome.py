"""Outcome models for CASIL decisions."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .errors import (
    CASIL_POLICY_ALLOWED,
    CASIL_POLICY_BLOCKED_SECRET,
    CASIL_POLICY_OVERSIZE,
    CASIL_POLICY_REDACTED,
    CASIL_INTERNAL_ERROR,
)


class CASILDecision:
    """Enumerated decision outcomes."""

    ALLOW = "ALLOW"
    ALLOW_WITH_REDACTION = "ALLOW_WITH_REDACTION"
    BLOCK = "BLOCK"


@dataclass
class CASILClassification:
    """Classification result for a message."""

    kind: str = "unknown"
    risk_level: str = "unknown"
    flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class CASILOutcome:
    """Structured outcome from CASIL engine."""

    decision: str = CASILDecision.ALLOW
    reason_code: str = CASIL_POLICY_ALLOWED
    classification: CASILClassification = field(default_factory=CASILClassification)
    redacted_payload: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    internal_error: Optional[str] = None

    @property
    def should_block(self) -> bool:
        return self.decision == CASILDecision.BLOCK

    @property
    def should_redact_transport(self) -> bool:
        return self.decision == CASILDecision.ALLOW_WITH_REDACTION and self.metadata.get("transport_redaction", False)
