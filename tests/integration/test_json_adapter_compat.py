import json
from datetime import datetime, timezone

import pytest

from arqonbus.protocol.envelope import Envelope


@pytest.mark.integration
def test_json_adapter_is_compatible_with_protobuf_round_trip():
    original = Envelope(
        id="arq_33333333333333333333333333",
        timestamp=datetime.now(timezone.utc),
        type="command",
        room="ops",
        channel="control",
        command="op.continuum.projector.status",
        args={"tenant_id": "tenant-a", "limit": 10},
        payload={"human_view": True},
        metadata={
            "tenant_id": "tenant-a",
            "sequence": 7,
            "vector_clock": {"node-a": 7},
            "causal_parent_id": "arq_22222222222222222222222222",
        },
    )

    proto_bytes = original.to_proto_bytes()
    recovered = Envelope.from_proto_bytes(proto_bytes)
    json_view = recovered.to_json()
    final = Envelope.from_json(json_view)
    json_obj = json.loads(json_view)

    assert json_obj["type"] == "command"
    assert final.command == "op.continuum.projector.status"
    assert final.args["tenant_id"] == "tenant-a"
    assert final.metadata["sequence"] == 7
    assert final.metadata["vector_clock"]["node-a"] == 7
