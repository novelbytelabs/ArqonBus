import pytest

from arqonbus.casil.integration import CasilIntegration
from arqonbus.casil.outcome import CASILDecision
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope


@pytest.mark.asyncio
async def test_mode_switch_changes_outcome():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "monitor"
    cfg.policies.block_on_probable_secret = True
    cfg.policies.redaction.patterns = [r"token"]
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="secure", channel="ops", payload={"data": "token-123"})

    outcome_monitor = await casil.process(envelope, {"client_id": "c1"})
    cfg.mode = "enforce"
    casil_enforce = CasilIntegration(cfg)
    envelope2 = Envelope(type="message", room="secure", channel="ops", payload={"data": "token-123"})
    outcome_enforce = await casil_enforce.process(envelope2, {"client_id": "c1"})

    assert outcome_monitor.decision != CASILDecision.BLOCK
    assert outcome_enforce.decision in (CASILDecision.BLOCK, CASILDecision.ALLOW_WITH_REDACTION)
