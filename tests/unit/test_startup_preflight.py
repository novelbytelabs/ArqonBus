from arqonbus.config.config import ArqonBusConfig, startup_preflight_errors


def test_storage_mode_and_redis_url_load_from_environment(monkeypatch):
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.setenv("ARQONBUS_REDIS_URL", "redis://127.0.0.1:6379/0")

    cfg = ArqonBusConfig.from_environment()

    assert cfg.storage.mode == "strict"
    assert cfg.storage.redis_url == "redis://127.0.0.1:6379/0"


def test_startup_preflight_strict_requires_explicit_core_env(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "true")
    monkeypatch.delenv("ARQONBUS_SERVER_HOST", raising=False)
    monkeypatch.delenv("ARQONBUS_SERVER_PORT", raising=False)
    monkeypatch.delenv("ARQONBUS_STORAGE_MODE", raising=False)

    cfg = ArqonBusConfig()
    errors = startup_preflight_errors(cfg)

    assert any("ARQONBUS_SERVER_HOST" in e for e in errors)
    assert any("ARQONBUS_SERVER_PORT" in e for e in errors)
    assert any("ARQONBUS_STORAGE_MODE" in e for e in errors)


def test_startup_preflight_strict_storage_requires_redis_url(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "true")
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.delenv("ARQONBUS_REDIS_URL", raising=False)

    cfg = ArqonBusConfig()
    cfg.storage.mode = "strict"
    cfg.storage.backend = "redis"
    cfg.storage.redis_url = None
    errors = startup_preflight_errors(cfg)

    assert any("ARQONBUS_REDIS_URL" in e for e in errors)


def test_startup_preflight_non_strict_allows_defaults(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "false")
    cfg = ArqonBusConfig()
    cfg.environment = "development"

    assert startup_preflight_errors(cfg) == []
