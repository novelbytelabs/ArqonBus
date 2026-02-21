from datetime import datetime, timezone

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.validator import EnvelopeValidator


def test_envelope_time_metadata_accepts_valid_sequence_vector_clock():
    envelope = Envelope(
        id="arq_1700000000000000000_1_abc123",
        timestamp=datetime.now(timezone.utc),
        type="message",
        version="1.0",
        payload={"ok": True},
        metadata={
            "sequence": 4,
            "vector_clock": {"node-a": 4, "node-b": 1},
            "causal_parent_id": "arq_1700000000000000000_2_def456",
        },
    )
    assert EnvelopeValidator.validate_envelope(envelope) == []


def test_envelope_time_metadata_rejects_invalid_vector_clock_shape():
    envelope = Envelope(
        id="arq_1700000000000000000_3_aaa111",
        timestamp=datetime.now(timezone.utc),
        type="message",
        version="1.0",
        payload={"ok": True},
        metadata={"vector_clock": {"node-a": -1}},
    )
    errors = EnvelopeValidator.validate_envelope(envelope)
    assert any("vector_clock values" in err for err in errors)
