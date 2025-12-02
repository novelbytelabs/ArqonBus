"""Deterministic CASIL classifier."""

import json
import re
from typing import Any, Dict

from ..protocol.envelope import Envelope
from ..config.config import CASILConfig
from .outcome import CASILClassification


DEFAULT_SECRET_PATTERNS = [
    r"(?i)api[_-]?key",
    r"(?i)secret",
    r"(?i)token",
    r"(?i)password",
    r"(?i)bearer\s+[A-Za-z0-9\-\._]+",
]


def _flatten_payload(payload: Any, max_bytes: int) -> str:
    """Serialize payload safely and truncate."""
    try:
        data = json.dumps(payload, ensure_ascii=True)
    except Exception:
        data = str(payload)
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data


def _detect_secret(data: str, patterns) -> bool:
    for pattern in patterns:
        if re.search(pattern, data):
            return True
    return False


def classify(envelope: Envelope, casil_config: CASILConfig, context: Dict[str, Any]) -> CASILClassification:
    """Classify a message in a bounded, deterministic way."""
    classification = CASILClassification(kind="unknown", risk_level="low", flags={})

    if envelope.type == "command":
        classification.kind = "control"
    elif envelope.type == "telemetry":
        classification.kind = "telemetry"
    elif envelope.type == "message":
        classification.kind = "data"
    elif envelope.type == "error":
        classification.kind = "system"

    serialized = _flatten_payload(envelope.payload, casil_config.limits.max_inspect_bytes)
    patterns = casil_config.policies.redaction.patterns or DEFAULT_SECRET_PATTERNS
    if _detect_secret(serialized, patterns):
        classification.flags["contains_probable_secret"] = True
        classification.risk_level = "high"

    if context.get("oversize_payload"):
        classification.flags["oversize_payload"] = True
        classification.risk_level = "medium" if classification.risk_level == "low" else classification.risk_level

    if casil_config.mode == "enforce" and classification.flags:
        classification.risk_level = "high" if classification.flags.get("contains_probable_secret") else classification.risk_level

    return classification
