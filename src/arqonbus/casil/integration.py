"""CASIL integration points for ArqonBus pipeline."""

import logging
from typing import Any, Dict, Optional

from ..protocol.envelope import Envelope
from ..telemetry.emitter import get_emitter
from ..config.config import CASILConfig
from .engine import CASILEngine
from .outcome import CASILOutcome, CASILDecision
from .errors import (
    CASIL_POLICY_BLOCKED_SECRET,
    CASIL_POLICY_OVERSIZE,
    CASIL_INTERNAL_ERROR,
    CASIL_DISABLED,
    CASIL_OUT_OF_SCOPE,
)


logger = logging.getLogger(__name__)


class CasilIntegration:
    """Integration shim between CASIL engine and ArqonBus pipeline."""

    def __init__(self, casil_config: CASILConfig):
        self.config = casil_config
        self.engine = CASILEngine(casil_config)
        self.telemetry_emitter = get_emitter()

    async def process(self, envelope: Envelope, context: Dict[str, Any]) -> CASILOutcome:
        """Process an envelope through CASIL and return the outcome."""
        outcome = self.engine.inspect(envelope, context)
        if outcome.reason_code in (CASIL_DISABLED, CASIL_OUT_OF_SCOPE):
            return outcome
        await self._emit_telemetry(envelope, outcome, context)
        if self.config.metadata.to_logs:
            self._log_outcome(envelope, outcome)
        if self.config.metadata.to_envelope and outcome.classification:
            envelope.metadata["casil"] = {
                "kind": outcome.classification.kind,
                "risk_level": outcome.classification.risk_level,
                "flags": outcome.classification.flags,
                "reason_code": outcome.reason_code,
                "decision": outcome.decision,
            }
        if outcome.should_redact_transport:
            envelope.payload = outcome.redacted_payload or envelope.payload
        return outcome

    def _log_outcome(self, envelope: Envelope, outcome: CASILOutcome):
        if outcome.decision == CASILDecision.BLOCK:
            logger.warning(
                "CASIL blocked message %s in %s:%s reason=%s",
                envelope.id,
                envelope.room,
                envelope.channel,
                outcome.reason_code,
            )
        elif outcome.decision == CASILDecision.ALLOW_WITH_REDACTION:
            logger.info(
                "CASIL redacted message %s in %s:%s reason=%s",
                envelope.id,
                envelope.room,
                envelope.channel,
                outcome.reason_code,
            )

    async def _emit_telemetry(self, envelope: Envelope, outcome: CASILOutcome, context: Dict[str, Any]):
        emitter = self.telemetry_emitter or get_emitter()
        if not emitter or not self.config.metadata.to_telemetry:
            return

        metadata = {
            "decision": outcome.decision,
            "reason_code": outcome.reason_code,
            "flags": outcome.classification.flags if outcome.classification else {},
            "room": envelope.room or context.get("room"),
            "channel": envelope.channel or context.get("channel"),
        }
        if outcome.internal_error:
            metadata["internal_error"] = outcome.internal_error

        try:
            await emitter.emit_event(
                event_type="casil_decision",
                client_id=context.get("client_id"),
                message_id=envelope.id,
                metadata=metadata,
                severity="warning" if outcome.decision == CASILDecision.BLOCK else "info",
            )
        except Exception as exc:
            logger.error("Failed to emit CASIL telemetry: %s", exc)
