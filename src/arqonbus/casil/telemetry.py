"""Telemetry helpers for CASIL."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CASILTelemetryEvent:
    """Structured CASIL telemetry event."""

    decision: str
    reason_code: str
    room: str = ""
    channel: str = ""
    flags: Dict[str, Any] = None
    internal_error: str = ""


def build_event(decision: str, reason_code: str, room: str, channel: str, flags: Dict[str, Any], internal_error: str = "") -> Dict[str, Any]:
    return {
        "decision": decision,
        "reason_code": reason_code,
        "room": room,
        "channel": channel,
        "flags": flags or {},
        "internal_error": internal_error,
    }
