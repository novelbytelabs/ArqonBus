from datetime import datetime, timezone

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.protocol.protobuf_codec import envelope_from_proto_bytes, envelope_to_proto_bytes
from arqonbus.protocol.validator import EnvelopeValidator


def test_envelope_protobuf_round_trip_preserves_core_fields():
    envelope = Envelope(
        id=generate_message_id(),
        timestamp=datetime.now(timezone.utc),
        type="command",
        room="ops",
        channel="control",
        sender="client-a",
        command="op.continuum.projector.status",
        args={"tenant_id": "tenant-1", "limit": 10},
        payload={"content": "ping"},
        metadata={"tenant_id": "tenant-1", "twist_id": "tw-1"},
        version="1.0",
    )

    raw = envelope_to_proto_bytes(envelope)
    decoded = envelope_from_proto_bytes(raw)

    assert decoded.id == envelope.id
    assert decoded.type == "command"
    assert decoded.room == "ops"
    assert decoded.channel == "control"
    assert decoded.command == envelope.command
    assert decoded.args["tenant_id"] == "tenant-1"
    assert decoded.payload["content"] == "ping"
    assert decoded.metadata["tenant_id"] == "tenant-1"


def test_validator_can_parse_protobuf_wire_payload():
    envelope = Envelope(
        id=generate_message_id(),
        timestamp=datetime.now(timezone.utc),
        type="message",
        room="ops",
        channel="events",
        payload={"x": 1},
    )
    wire = envelope.to_proto_bytes()
    parsed, errors, wire_format = EnvelopeValidator.validate_and_parse_wire(wire)
    assert wire_format == "protobuf"
    assert not errors
    assert parsed.id == envelope.id
