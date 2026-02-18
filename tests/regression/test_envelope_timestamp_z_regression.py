from arqonbus.protocol.envelope import Envelope


def test_envelope_from_dict_accepts_rfc3339_z_suffix():
    envelope = Envelope.from_dict(
        {
            "id": "msg-zulu-1",
            "type": "message",
            "version": "1.0",
            "timestamp": "2026-02-18T00:00:00Z",
            "payload": {"content": "hello"},
        }
    )

    assert envelope.timestamp.isoformat().endswith("+00:00")
    assert envelope.payload["content"] == "hello"


def test_envelope_from_json_accepts_rfc3339_z_suffix():
    raw = (
        '{"id":"msg-zulu-2","type":"message","version":"1.0",'
        '"timestamp":"2026-02-18T01:02:03Z","payload":{"content":"world"}}'
    )
    envelope = Envelope.from_json(raw)
    assert envelope.timestamp.isoformat().endswith("+00:00")
    assert envelope.payload["content"] == "world"
