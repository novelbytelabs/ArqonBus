from arqonbus.casil.telemetry import build_event


def test_build_event_contains_expected_fields():
    event = build_event("ALLOW", "CASIL_POLICY_ALLOWED", "room", "channel", {"flag": True})
    assert event["decision"] == "ALLOW"
    assert event["reason_code"]
    assert "flags" in event
