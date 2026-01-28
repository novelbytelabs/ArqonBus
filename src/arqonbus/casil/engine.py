"""CASIL engine orchestrating scope, classification, policies, and redaction."""

from typing import Any, Dict

from ..protocol.envelope import Envelope
from ..config.config import CASILConfig, get_config
from .scope import in_scope
from .classifier import classify
from .policies import evaluate_policies
from .redaction import redact_payload
from .outcome import CASILOutcome, CASILDecision
from .errors import (
    CASIL_DISABLED,
    CASIL_OUT_OF_SCOPE,
    CASIL_INTERNAL_ERROR,
    CASIL_POLICY_ALLOWED,
    CASIL_MONITOR_MODE,
)

# Holonomy Engine (Rust-based fast path)
try:
    from ..holonomy import check as holonomy_check, HolonomyVerdict
    HOLONOMY_AVAILABLE = True
except ImportError:
    HOLONOMY_AVAILABLE = False
    HolonomyVerdict = None  # type: ignore

HOLONOMY_SAFE = "HOLONOMY_SAFE"  # New reason code


class CASILEngine:
    """Content-Aware Safety & Inspection Layer engine."""

    def __init__(self, casil_config: CASILConfig):
        self.config = casil_config

    def inspect(self, envelope: Envelope, context: Dict[str, Any]) -> CASILOutcome:
        """Inspect an envelope and return CASILOutcome."""
        if not self.config.enabled:
            return CASILOutcome(decision=CASILDecision.ALLOW, reason_code=CASIL_DISABLED)

        room = envelope.room or context.get("room")
        channel = envelope.channel or context.get("channel")
        room_channel = f"{room}:{channel}" if room and channel else room or channel or ""

        if not in_scope(room, channel, self.config):
            return CASILOutcome(decision=CASILDecision.ALLOW, reason_code=CASIL_OUT_OF_SCOPE)

        # --- HOLONOMY FAST PATH ---
        # If Holonomy is enabled, run the Rust check FIRST.
        # Via Negativa: If it's SAFE, we trust it. If BLOCK, we block. If AMBIGUOUS, continue.
        global_config = get_config()
        if HOLONOMY_AVAILABLE and global_config.holonomy_enabled:
            payload_text = str(envelope.payload) if envelope.payload else ""
            verdict = holonomy_check(payload_text)
            if verdict == HolonomyVerdict.SAFE:
                return CASILOutcome(decision=CASILDecision.ALLOW, reason_code=HOLONOMY_SAFE)
            elif verdict == HolonomyVerdict.BLOCK:
                return CASILOutcome(decision=CASILDecision.BLOCK, reason_code="HOLONOMY_BLOCK")
            # else: AMBIGUOUS -> fall through to legacy CASIL logic

        try:
            payload_len = len(envelope.payload) if isinstance(envelope.payload, (list, dict, str)) else 0
            policy_context = {"oversize_payload": payload_len > self.config.limits.max_inspect_bytes}
            classification = classify(envelope, self.config, policy_context)
            policy_result = evaluate_policies(envelope, self.config, classification.flags)

            decision = CASILDecision.ALLOW
            reason_code = policy_result["reason_code"] or CASIL_POLICY_ALLOWED
            redacted_payload = None

            redaction_needed = policy_result["should_redact"] or bool(
                self.config.policies.redaction.paths
                or self.config.policies.redaction.patterns
                or self.config.policies.redaction.never_log_payload_for
            )
            if redaction_needed:
                redacted_payload = redact_payload(envelope.payload, self.config, target="logs", room_channel=room_channel)

            if policy_result["should_block"] and self.config.mode == "enforce":
                decision = CASILDecision.BLOCK
            elif redaction_needed:
                decision = CASILDecision.ALLOW_WITH_REDACTION
            else:
                decision = CASILDecision.ALLOW

            if self.config.mode == "monitor" and decision == CASILDecision.BLOCK:
                # Downgrade to allow with metadata in monitor mode
                decision = CASILDecision.ALLOW_WITH_REDACTION if policy_result["should_redact"] else CASILDecision.ALLOW
                reason_code = CASIL_MONITOR_MODE

            outcome = CASILOutcome(
                decision=decision,
                reason_code=reason_code,
                classification=classification,
                redacted_payload=redacted_payload,
                metadata={
                    "flags": classification.flags,
                    "mode": self.config.mode,
                    "room": room,
                    "channel": channel,
                    "transport_redaction": self.config.policies.redaction.transport_redaction,
                },
            )
            return outcome

        except Exception as exc:
            fallback_decision = (
                CASILDecision.BLOCK if self.config.default_decision == "block" else CASILDecision.ALLOW
            )
            return CASILOutcome(
                decision=fallback_decision,
                reason_code=CASIL_INTERNAL_ERROR,
                internal_error=str(exc),
            )
