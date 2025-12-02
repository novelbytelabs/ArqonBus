"""CASIL redaction helpers."""

import copy
import json
import re
from fnmatch import fnmatch
from typing import Any, List

from ..config.config import CASILConfig

REDACT_TOKEN = "***REDACTED***"


def _redact_paths(obj: Any, paths: List[str], depth: int = 0, max_depth: int = 10) -> Any:
    """Redact fields by path name within JSON-like structures."""
    if depth > max_depth:
        return obj

    if isinstance(obj, dict):
        redacted = {}
        for key, value in obj.items():
            if key in paths:
                redacted[key] = REDACT_TOKEN
            else:
                redacted[key] = _redact_paths(value, paths, depth + 1, max_depth)
        return redacted
    if isinstance(obj, list):
        return [_redact_paths(item, paths, depth + 1, max_depth) for item in obj]
    return obj


def _redact_patterns(text: str, patterns: List[str]) -> str:
    redacted_text = text
    for pattern in patterns:
        try:
            redacted_text = re.sub(pattern, REDACT_TOKEN, redacted_text)
        except re.error:
            continue
    return redacted_text


def redact_payload(payload: Any, casil_config: CASILConfig, target: str, room_channel: str) -> Any:
    """Redact payload for observability or transport targets."""
    redaction_cfg = casil_config.policies.redaction
    apply_full_redaction = any(
        fnmatch(room_channel, pattern) for pattern in redaction_cfg.never_log_payload_for
    ) if redaction_cfg.never_log_payload_for else False

    if apply_full_redaction and target in ("logs", "telemetry"):
        return REDACT_TOKEN

    working = copy.deepcopy(payload)
    if isinstance(working, (dict, list)):
        working = _redact_paths(working, redaction_cfg.paths or [])
    else:
        # Non-structured payloads are handled below via pattern replacement
        pass

    try:
        serialized = json.dumps(working, ensure_ascii=True)
    except Exception:
        serialized = str(working)

    patterns = (redaction_cfg.patterns or [])[: casil_config.limits.max_patterns or None]
    if patterns:
        serialized = _redact_patterns(serialized, patterns)

    try:
        return json.loads(serialized)
    except Exception:
        # Fallback to string to ensure well-formed output
        return serialized
