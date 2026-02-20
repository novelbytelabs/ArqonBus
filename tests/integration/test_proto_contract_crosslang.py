from pathlib import Path

import pytest

from arqonbus.protocol.validator import EnvelopeValidator


@pytest.mark.integration
def test_cross_language_protobuf_fixture_is_parseable_by_python_validator():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "crates"
        / "proto"
        / "tests"
        / "fixtures"
        / "python_envelope.bin"
    )
    payload = fixture.read_bytes()
    envelope, errors, wire_format = EnvelopeValidator.validate_and_parse_wire(payload)

    assert wire_format == "protobuf"
    assert not errors
    assert envelope.command == "op.continuum.projector.status"
