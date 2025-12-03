"""CASIL policy evaluation."""

import json
import re
from typing import Any, Dict, Optional

from ..protocol.envelope import Envelope
from ..config.config import CASILConfig
from .errors import CASIL_POLICY_BLOCKED_SECRET, CASIL_POLICY_OVERSIZE, CASIL_POLICY_REDACTED, CASIL_POLICY_ALLOWED


def _serialized_length(payload: Any) -> int:
    try:
        return len(json.dumps(payload, ensure_ascii=True))
    except Exception:
        return len(str(payload))


def _detect_probable_secret(payload: Any, patterns, max_inspect_bytes: int) -> bool:
    try:
        data = json.dumps(payload, ensure_ascii=True)
    except Exception:
        data = str(payload)
    data = data[:max_inspect_bytes]
    for pattern in patterns:
        if re.search(pattern, data):
            return True
    return False


def evaluate_policies(
    envelope: Envelope,
    casil_config: CASILConfig,
    classification_flags: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """
    Evaluate CASIL policies for the given envelope.

    The logic here is intentionally conservative:
    - Oversize payloads can be blocked regardless of content.
    - "Probable secret" detection comes from:
        * classifier flags (contains_probable_secret), and/or
        * regex patterns in casil.policies.redaction.patterns
    - If block_on_probable_secret is True, any probable secret causes a block.
    - Otherwise, probable secrets cause redaction but not a hard block.
    """
    flags: Dict[str, bool] = dict(classification_flags or {})
    payload_len = _serialized_length(envelope.payload)

    should_block = False
    should_redact = False
    reason_code = CASIL_POLICY_ALLOWED

    # 1) Oversize payload check
    if casil_config.policies.max_payload_bytes and payload_len > casil_config.policies.max_payload_bytes:
        flags["oversize_payload"] = True
        should_block = True
        reason_code = CASIL_POLICY_OVERSIZE

    # 2) Probable-secret detection
    #    Start with what the classifier already decided…
    probable_secret = bool(flags.get("contains_probable_secret"))

    #    …then OR in any matches from configured redaction patterns
    patterns = (casil_config.policies.redaction.patterns or [])[: casil_config.limits.max_patterns or None]
    if patterns and (casil_config.policies.block_on_probable_secret or casil_config.mode == "enforce"):
        try:
            if _detect_probable_secret(envelope.payload, patterns, casil_config.limits.max_inspect_bytes):
                probable_secret = True
                flags["contains_probable_secret"] = True
        except ValueError:
            # If payload can't be inspected, leave probable_secret as-is
            pass

    # 3) Apply policy based on probable_secret + mode/config
    if (casil_config.policies.block_on_probable_secret or casil_config.mode == "enforce") and probable_secret:
        # We always redact when we think it's a secret
        should_redact = True

        # And optionally block, depending on config
        if casil_config.policies.block_on_probable_secret:
            should_block = True
            reason_code = CASIL_POLICY_BLOCKED_SECRET

    # 4) Final decision outcome
    if not should_block and should_redact:
        decision = CASIL_POLICY_REDACTED
        reason_code = CASIL_POLICY_REDACTED
    elif should_block:
        decision = reason_code
    else:
        decision = CASIL_POLICY_ALLOWED

    return {
        "should_block": should_block,
        "should_redact": should_redact,
        "reason_code": reason_code,
        "flags": flags,
    }
