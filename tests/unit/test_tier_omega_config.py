from arqonbus.config.config import ArqonBusConfig


def test_tier_omega_config_loads_from_environment(monkeypatch):
    monkeypatch.setenv("ARQONBUS_OMEGA_ENABLED", "true")
    monkeypatch.setenv("ARQONBUS_OMEGA_LAB_ROOM", "omega-room")
    monkeypatch.setenv("ARQONBUS_OMEGA_LAB_CHANNEL", "omega-signals")
    monkeypatch.setenv("ARQONBUS_OMEGA_MAX_EVENTS", "17")
    monkeypatch.setenv("ARQONBUS_OMEGA_MAX_SUBSTRATES", "9")
    monkeypatch.setenv("ARQONBUS_OMEGA_RUNTIME", "firecracker")
    monkeypatch.setenv("ARQONBUS_OMEGA_FIRECRACKER_BIN", "/usr/local/bin/firecracker")
    monkeypatch.setenv("ARQONBUS_OMEGA_KERNEL_IMAGE", "/tmp/vmlinux.bin")
    monkeypatch.setenv("ARQONBUS_OMEGA_ROOTFS_IMAGE", "/tmp/rootfs.ext4")
    monkeypatch.setenv("ARQONBUS_OMEGA_MAX_VMS", "4")

    cfg = ArqonBusConfig.from_environment()

    assert cfg.tier_omega.enabled is True
    assert cfg.tier_omega.lab_room == "omega-room"
    assert cfg.tier_omega.lab_channel == "omega-signals"
    assert cfg.tier_omega.max_events == 17
    assert cfg.tier_omega.max_substrates == 9
    assert cfg.tier_omega.runtime == "firecracker"
    assert cfg.tier_omega.firecracker_bin == "/usr/local/bin/firecracker"
    assert cfg.tier_omega.kernel_image == "/tmp/vmlinux.bin"
    assert cfg.tier_omega.rootfs_image == "/tmp/rootfs.ext4"
    assert cfg.tier_omega.max_vms == 4


def test_tier_omega_config_validation_guards_invalid_values():
    cfg = ArqonBusConfig()
    cfg.tier_omega.lab_room = ""
    cfg.tier_omega.lab_channel = ""
    cfg.tier_omega.max_events = 0
    cfg.tier_omega.max_substrates = 0
    cfg.tier_omega.runtime = "unknown"
    cfg.tier_omega.max_vms = 0

    errors = cfg.validate()

    assert "Tier-Omega lab_room must be non-empty" in errors
    assert "Tier-Omega lab_channel must be non-empty" in errors
    assert "Tier-Omega max_events must be >= 1" in errors
    assert "Tier-Omega max_substrates must be >= 1" in errors
    assert "Tier-Omega runtime must be one of: memory, firecracker" in errors
    assert "Tier-Omega max_vms must be >= 1" in errors


def test_tier_omega_firecracker_requires_images_when_enabled():
    cfg = ArqonBusConfig()
    cfg.tier_omega.enabled = True
    cfg.tier_omega.runtime = "firecracker"
    cfg.tier_omega.kernel_image = None
    cfg.tier_omega.rootfs_image = None

    errors = cfg.validate()

    assert "Tier-Omega firecracker runtime requires ARQONBUS_OMEGA_KERNEL_IMAGE" in errors
    assert "Tier-Omega firecracker runtime requires ARQONBUS_OMEGA_ROOTFS_IMAGE" in errors


def test_tier_omega_config_exposed_in_to_dict():
    cfg = ArqonBusConfig()
    cfg.tier_omega.enabled = True
    cfg.tier_omega.lab_room = "omega-lab"
    cfg.tier_omega.lab_channel = "signals"
    cfg.tier_omega.max_events = 25
    cfg.tier_omega.max_substrates = 7
    cfg.tier_omega.runtime = "firecracker"
    cfg.tier_omega.max_vms = 3

    data = cfg.to_dict()

    assert data["tier_omega"]["enabled"] is True
    assert data["tier_omega"]["lab_room"] == "omega-lab"
    assert data["tier_omega"]["lab_channel"] == "signals"
    assert data["tier_omega"]["max_events"] == 25
    assert data["tier_omega"]["max_substrates"] == 7
    assert data["tier_omega"]["runtime"] == "firecracker"
    assert data["tier_omega"]["max_vms"] == 3
