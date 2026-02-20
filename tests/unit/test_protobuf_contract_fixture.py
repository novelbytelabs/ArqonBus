from pathlib import Path

from arqonbus.protocol.envelope import Envelope


def test_python_decodes_shared_protobuf_fixture():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "crates"
        / "proto"
        / "tests"
        / "fixtures"
        / "python_envelope.bin"
    )
    wire = fixture.read_bytes()
    envelope = Envelope.from_proto_bytes(wire)

    assert envelope.id == "arq_01HZZZZZZZZZZZZZZZZZZZZZZZ"
    assert envelope.type == "command"
    assert envelope.command == "op.continuum.projector.status"
    assert envelope.room == "ops"
    assert envelope.channel == "control"
    assert envelope.metadata["tenant_id"] == "tenant-fixture"
    assert envelope.args["tenant_id"] == "tenant-fixture"
