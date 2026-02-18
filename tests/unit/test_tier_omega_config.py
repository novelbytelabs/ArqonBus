from arqonbus.config.config import ArqonBusConfig


def test_tier_omega_config_loads_from_environment(monkeypatch):
    monkeypatch.setenv("ARQONBUS_OMEGA_ENABLED", "true")
    monkeypatch.setenv("ARQONBUS_OMEGA_LAB_ROOM", "omega-room")
    monkeypatch.setenv("ARQONBUS_OMEGA_LAB_CHANNEL", "omega-signals")
    monkeypatch.setenv("ARQONBUS_OMEGA_MAX_EVENTS", "17")

    cfg = ArqonBusConfig.from_environment()

    assert cfg.tier_omega.enabled is True
    assert cfg.tier_omega.lab_room == "omega-room"
    assert cfg.tier_omega.lab_channel == "omega-signals"
    assert cfg.tier_omega.max_events == 17


def test_tier_omega_config_validation_guards_invalid_values():
    cfg = ArqonBusConfig()
    cfg.tier_omega.lab_room = ""
    cfg.tier_omega.lab_channel = ""
    cfg.tier_omega.max_events = 0

    errors = cfg.validate()

    assert "Tier-Omega lab_room must be non-empty" in errors
    assert "Tier-Omega lab_channel must be non-empty" in errors
    assert "Tier-Omega max_events must be >= 1" in errors


def test_tier_omega_config_exposed_in_to_dict():
    cfg = ArqonBusConfig()
    cfg.tier_omega.enabled = True
    cfg.tier_omega.lab_room = "omega-lab"
    cfg.tier_omega.lab_channel = "signals"
    cfg.tier_omega.max_events = 25

    data = cfg.to_dict()

    assert data["tier_omega"]["enabled"] is True
    assert data["tier_omega"]["lab_room"] == "omega-lab"
    assert data["tier_omega"]["lab_channel"] == "signals"
    assert data["tier_omega"]["max_events"] == 25
