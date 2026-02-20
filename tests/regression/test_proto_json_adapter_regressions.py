from datetime import datetime, timezone

from arqonbus.protocol.envelope import Envelope


def test_proto_json_adapter_preserves_command_and_args():
    original = Envelope(
        id="arq_1700000000000000000_7_c0ffee",
        timestamp=datetime.now(timezone.utc),
        type="command",
        version="1.0",
        command="op.store.get",
        args={"namespace": "tenant:alpha", "key": "k1"},
        payload={"request": "state"},
        metadata={"sequence": 9, "vector_clock": {"node-x": 9}},
    )

    proto_roundtrip = Envelope.from_proto_bytes(original.to_proto_bytes())
    json_roundtrip = Envelope.from_json(proto_roundtrip.to_json())

    assert json_roundtrip.command == "op.store.get"
    assert json_roundtrip.args["key"] == "k1"
    assert json_roundtrip.metadata["sequence"] == 9
