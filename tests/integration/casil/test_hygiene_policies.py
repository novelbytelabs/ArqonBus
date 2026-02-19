import pytest

from arqonbus.casil.integration import CasilIntegration
from arqonbus.casil.outcome import CASILDecision
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope


@pytest.mark.asyncio
async def test_enforce_blocks_secret():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "enforce"
    cfg.policies.block_on_probable_secret = True
    cfg.policies.redaction.patterns = [r"token"]
    cfg.scope.include = ["secure-*"]
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="secure-room", channel="ops", payload={"data": "token-123"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision in (CASILDecision.BLOCK, CASILDecision.ALLOW_WITH_REDACTION)
    assert outcome.reason_code


@pytest.mark.asyncio
async def test_monitor_does_not_block_secret():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "monitor"
    cfg.policies.block_on_probable_secret = True
    cfg.policies.redaction.patterns = [r"token"]
    cfg.scope.include = ["secure-*"]
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="secure-room", channel="ops", payload={"data": "token-123"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision != CASILDecision.BLOCK
