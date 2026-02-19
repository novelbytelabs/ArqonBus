import asyncio

import pytest

from arqonbus.casil.integration import CasilIntegration
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.casil.outcome import CASILDecision


@pytest.mark.asyncio
async def test_monitor_mode_allows_with_metadata():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "monitor"
    cfg.scope.include = ["secure-*"]
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="secure-room", channel="updates", payload={"ping": "pong"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision in (CASILDecision.ALLOW, CASILDecision.ALLOW_WITH_REDACTION)


@pytest.mark.asyncio
async def test_enforce_out_of_scope_bypasses():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "enforce"
    cfg.scope.include = ["secure-*"]
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="public", channel="chat", payload={"ping": "pong"})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision == CASILDecision.ALLOW


@pytest.mark.asyncio
async def test_enforce_blocks_oversize():
    cfg = CASILConfig(enabled=True)
    cfg.mode = "enforce"
    cfg.policies.max_payload_bytes = 10
    casil = CasilIntegration(cfg)
    envelope = Envelope(type="message", room="secure-room", channel="updates", payload={"data": "x" * 50})

    outcome = await casil.process(envelope, {"client_id": "c1"})
    assert outcome.decision in (CASILDecision.BLOCK, CASILDecision.ALLOW_WITH_REDACTION)
