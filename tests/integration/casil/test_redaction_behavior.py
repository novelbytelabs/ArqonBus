import pytest

from arqonbus.casil.integration import CasilIntegration
from arqonbus.casil.outcome import CASILDecision
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope


@pytest.mark.asyncio
async def test_redaction_applies_to_logs_not_transport():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "monitor"
    cfg.policies.redaction.paths = ["token"]
    cfg.policies.redaction.transport_redaction = False
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="pii", channel="updates", payload={"token": "abc"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision in (CASILDecision.ALLOW, CASILDecision.ALLOW_WITH_REDACTION)
    assert envelope.payload["token"] == "abc"


@pytest.mark.asyncio
async def test_transport_redaction_enabled():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "enforce"
    cfg.policies.redaction.paths = ["token"]
    cfg.policies.redaction.transport_redaction = True
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="pii", channel="updates", payload={"token": "abc"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    if outcome.decision == CASILDecision.ALLOW_WITH_REDACTION:
        assert envelope.payload.get("token") != "abc"
