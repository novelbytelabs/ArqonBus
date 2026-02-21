from datetime import datetime, timezone

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.validator import EnvelopeValidator


def test_protobuf_unknown_fields_do_not_break_round_trip():
    original = Envelope(
        id="arq_1700000000000000000_8_a1b2c3",
        timestamp=datetime.now(timezone.utc),
        type="command",
        version="1.0",
        command="op.continuum.projector.status",
        args={"tenant_id": "tenant-a"},
        metadata={"sequence": 11},
    )

    proto_payload = original.to_proto_bytes()

    # Append unknown varint field #200 with value=1; decoder must ignore it.
    proto_payload_with_unknown = proto_payload + b"\xc0\x0c\x01"

    recovered = Envelope.from_proto_bytes(proto_payload_with_unknown)
    parsed, errors, wire_format = EnvelopeValidator.validate_and_parse_wire(proto_payload_with_unknown)

    assert recovered.command == "op.continuum.projector.status"
    assert recovered.metadata["sequence"] == 11
    assert wire_format == "protobuf"
    assert parsed.id == original.id
    assert errors == []
