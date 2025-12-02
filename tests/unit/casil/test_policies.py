from arqonbus.casil.policies import evaluate_policies
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope


def test_policy_detects_oversize():
    cfg = CASILConfig(enabled=True)
    cfg.policies.max_payload_bytes = 5
    envelope = Envelope(type="message", payload={"data": "123456"}, room="secure", channel="room")
    result = evaluate_policies(envelope, cfg, {})
    assert result["should_block"]
    assert result["reason_code"]


def test_policy_detects_probable_secret():
    cfg = CASILConfig(enabled=True)
    cfg.policies.block_on_probable_secret = True
    cfg.policies.redaction.patterns = [r"secret"]
    envelope = Envelope(type="message", payload={"data": "super secret token"}, room="secure", channel="room")
    result = evaluate_policies(envelope, cfg, {})
    assert result["should_block"]
    assert result["reason_code"]
