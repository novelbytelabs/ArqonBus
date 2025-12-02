from arqonbus.casil.redaction import redact_payload, REDACT_TOKEN
from arqonbus.config.config import CASILConfig


def test_redact_paths_masks_fields():
    cfg = CASILConfig(enabled=True)
    cfg.policies.redaction.paths = ["password"]
    payload = {"username": "u", "password": "p"}
    result = redact_payload(payload, cfg, target="logs", room_channel="secure:updates")
    assert result["password"] == REDACT_TOKEN


def test_redact_patterns_masks_strings():
    cfg = CASILConfig(enabled=True)
    cfg.policies.redaction.patterns = [r"secret"]
    payload = {"note": "this is a secret"}
    result = redact_payload(payload, cfg, target="logs", room_channel="secure:updates")
    serialized = str(result)
    assert "secret" not in serialized


def test_never_log_payload_masks_all():
    cfg = CASILConfig(enabled=True)
    cfg.policies.redaction.never_log_payload_for = ["pii-*"]
    payload = {"ssn": "123-45-6789"}
    result = redact_payload(payload, cfg, target="logs", room_channel="pii-payroll:updates")
    assert result == REDACT_TOKEN
