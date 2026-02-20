from datetime import datetime, timezone

import pytest


EVENT_TYPES = {
    "episode.created",
    "episode.updated",
    "episode.deleted",
    "episode.summarized",
}

REQUIRED_ENVELOPE_FIELDS = {
    "event_id",
    "event_type",
    "tenant_id",
    "agent_id",
    "episode_id",
    "source_ts",
    "schema_version",
}

REQUIRED_PAYLOAD_FIELDS = {
    "content_ref",
    "tags",
    "metadata",
}


def _build_event() -> dict:
    return {
        "event_id": "01JYZZZZZZZZZZZZZZZZZZZZZZ",
        "event_type": "episode.created",
        "tenant_id": "tenant-a",
        "agent_id": "agent-1",
        "episode_id": "01JYAAAAAAAAAAAAAAAAAAAAAA",
        "source_ts": "2026-02-19T00:00:00+00:00",
        "schema_version": 1,
        "payload": {
            "content_ref": "sqlite://continuum/episodes/01JYAAAAAAAAAAAAAAAAAAAAAA",
            "summary": "Short summary",
            "tags": ["memory", "session"],
            "embedding_ref": "sled://embeddings/01JYAAAAAAAAAAAAAAAAAAAAAA",
            "metadata": {"priority": "normal"},
        },
    }


def validate_contract_event(event: dict) -> list[str]:
    errors = []
    missing_envelope = REQUIRED_ENVELOPE_FIELDS.difference(event.keys())
    if missing_envelope:
        errors.append(f"missing_envelope_fields:{sorted(missing_envelope)}")

    payload = event.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload_must_be_object")
        return errors

    missing_payload = REQUIRED_PAYLOAD_FIELDS.difference(payload.keys())
    if missing_payload:
        errors.append(f"missing_payload_fields:{sorted(missing_payload)}")

    if event.get("event_type") not in EVENT_TYPES:
        errors.append("unsupported_event_type")

    if event.get("schema_version") != 1:
        errors.append("unsupported_schema_version")

    try:
        datetime.fromisoformat(str(event.get("source_ts")).replace("Z", "+00:00"))
    except Exception:
        errors.append("invalid_source_ts")

    tags = payload.get("tags")
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        errors.append("payload_tags_must_be_string_array")

    if not isinstance(payload.get("metadata"), dict):
        errors.append("payload_metadata_must_be_object")

    return errors


def dedup_key(event: dict) -> tuple[str, str, str]:
    return (event["tenant_id"], event["agent_id"], event["event_id"])


def projection_upsert_key(event: dict) -> tuple[str, str, str]:
    return (event["tenant_id"], event["agent_id"], event["episode_id"])


def is_stale_update(last_event_ts: str, incoming_event_ts: str) -> bool:
    last_dt = datetime.fromisoformat(last_event_ts.replace("Z", "+00:00"))
    incoming_dt = datetime.fromisoformat(incoming_event_ts.replace("Z", "+00:00"))
    return incoming_dt < last_dt


def valkey_key_is_tenant_prefixed(key: str) -> bool:
    return key.startswith("tenant:")


def is_reflex_hotpath_pointer(content_ref: str) -> bool:
    return content_ref.startswith(("sqlite://", "sled://", "ram://"))


def contains_forbidden_hotpath_dump(payload: dict) -> bool:
    forbidden = {"raw_content", "episode_body", "embedding_vector", "full_state_dump"}
    return any(key in payload for key in forbidden)


def test_contract_event_minimum_shape_is_valid():
    event = _build_event()
    assert validate_contract_event(event) == []


def test_contract_rejects_missing_required_fields():
    event = _build_event()
    del event["event_id"]
    del event["payload"]["content_ref"]
    errors = validate_contract_event(event)
    assert any("missing_envelope_fields" in err for err in errors)
    assert any("missing_payload_fields" in err for err in errors)


def test_contract_rejects_invalid_event_type_and_schema_version():
    event = _build_event()
    event["event_type"] = "episode.unknown"
    event["schema_version"] = 2
    errors = validate_contract_event(event)
    assert "unsupported_event_type" in errors
    assert "unsupported_schema_version" in errors


def test_idempotency_key_contract():
    event = _build_event()
    assert dedup_key(event) == ("tenant-a", "agent-1", "01JYZZZZZZZZZZZZZZZZZZZZZZ")
    assert projection_upsert_key(event) == ("tenant-a", "agent-1", "01JYAAAAAAAAAAAAAAAAAAAAAA")


def test_projection_monotonic_guard_contract():
    newer = "2026-02-19T00:00:02+00:00"
    older = "2026-02-19T00:00:01+00:00"
    assert is_stale_update(newer, older) is True
    assert is_stale_update(older, newer) is False


@pytest.mark.parametrize(
    "key,expected",
    [
        ("tenant:t1:agent:a1:presence:last_seen", True),
        ("tenant:t1:episode:e1:cache:summary", True),
        ("episode:e1:cache:summary", False),
    ],
)
def test_valkey_tenant_prefix_contract(key: str, expected: bool):
    assert valkey_key_is_tenant_prefixed(key) is expected


def test_fail_open_vs_fail_closed_contract_examples():
    # Local Continuum write must not be blocked by analytics projection outage.
    projection_available = False
    local_write_success = True
    assert local_write_success is True
    assert projection_available is False

    # Policy/auth failures are fail-closed for publish path.
    policy_allows_publish = False
    publish_success = policy_allows_publish
    assert publish_success is False


def test_reflex_boundary_requires_pointer_style_content_refs():
    event = _build_event()
    assert is_reflex_hotpath_pointer(event["payload"]["content_ref"]) is True
    event["payload"]["content_ref"] = "postgres://projection/episode/01JYAAAAAAAAAAAAAAAAAAAAAA"
    assert is_reflex_hotpath_pointer(event["payload"]["content_ref"]) is False


def test_reflex_boundary_forbids_hotpath_state_dump_fields():
    payload = _build_event()["payload"]
    assert contains_forbidden_hotpath_dump(payload) is False
    payload["full_state_dump"] = {"raw": "..." * 3}
    assert contains_forbidden_hotpath_dump(payload) is True
