import pytest

from arqonbus.config.config import (
    ArqonBusConfig,
    load_config,
    normalize_environment_name,
    startup_preflight_errors,
)


def test_storage_mode_and_redis_url_load_from_environment(monkeypatch):
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.setenv("ARQONBUS_REDIS_URL", "redis://127.0.0.1:6379/0")

    cfg = ArqonBusConfig.from_environment()

    assert cfg.storage.mode == "strict"
    assert cfg.storage.redis_url == "redis://127.0.0.1:6379/0"


def test_storage_backend_accepts_valkey_alias(monkeypatch):
    monkeypatch.setenv("ARQONBUS_STORAGE_BACKEND", "valkey")
    cfg = ArqonBusConfig.from_environment()
    assert cfg.storage.backend == "valkey"


def test_storage_uses_valkey_url_alias(monkeypatch):
    monkeypatch.setenv("ARQONBUS_VALKEY_URL", "redis://127.0.0.1:6380/0")
    monkeypatch.delenv("ARQONBUS_REDIS_URL", raising=False)
    cfg = ArqonBusConfig.from_environment()
    assert cfg.storage.redis_url == "redis://127.0.0.1:6380/0"


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
    monkeypatch.delenv("ARQONBUS_VALKEY_URL", raising=False)

    cfg = ArqonBusConfig()
    cfg.storage.mode = "strict"
    cfg.storage.backend = "redis"
    cfg.storage.redis_url = None
    errors = startup_preflight_errors(cfg)

    assert any("ARQONBUS_REDIS_URL" in e for e in errors)


def test_startup_preflight_strict_storage_accepts_valkey_url(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "true")
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.setenv("ARQONBUS_VALKEY_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.delenv("ARQONBUS_REDIS_URL", raising=False)

    cfg = ArqonBusConfig()
    cfg.storage.mode = "strict"
    cfg.storage.backend = "valkey"
    cfg.storage.redis_url = None
    errors = startup_preflight_errors(cfg)

    assert not any("ARQONBUS_REDIS_URL" in e for e in errors)
    assert not any("ARQONBUS_VALKEY_URL" in e for e in errors)


def test_startup_preflight_strict_postgres_requires_url(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "true")
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.delenv("ARQONBUS_POSTGRES_URL", raising=False)

    cfg = ArqonBusConfig()
    cfg.storage.mode = "strict"
    cfg.storage.backend = "postgres"
    cfg.storage.postgres_url = None
    errors = startup_preflight_errors(cfg)

    assert any("ARQONBUS_POSTGRES_URL" in e for e in errors)


def test_prod_preflight_requires_dual_data_stack_by_default(monkeypatch):
    monkeypatch.delenv("ARQONBUS_PREFLIGHT_STRICT", raising=False)
    monkeypatch.delenv("ARQONBUS_REQUIRE_DUAL_DATA_STACK", raising=False)
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.delenv("ARQONBUS_REDIS_URL", raising=False)
    monkeypatch.delenv("ARQONBUS_VALKEY_URL", raising=False)
    monkeypatch.delenv("ARQONBUS_POSTGRES_URL", raising=False)

    cfg = ArqonBusConfig()
    cfg.environment = "prod"
    cfg.storage.mode = "strict"
    cfg.storage.backend = "postgres"
    errors = startup_preflight_errors(cfg)

    assert any("Dual data stack requires ARQONBUS_VALKEY_URL" in e for e in errors)
    assert any("Dual data stack requires ARQONBUS_POSTGRES_URL" in e for e in errors)


def test_prod_preflight_dual_data_stack_passes_when_both_urls_set(monkeypatch):
    monkeypatch.delenv("ARQONBUS_PREFLIGHT_STRICT", raising=False)
    monkeypatch.delenv("ARQONBUS_REQUIRE_DUAL_DATA_STACK", raising=False)
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.setenv("ARQONBUS_VALKEY_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("ARQONBUS_POSTGRES_URL", "postgresql://127.0.0.1:5432/arqonbus")

    cfg = ArqonBusConfig()
    cfg.environment = "prod"
    cfg.storage.mode = "strict"
    cfg.storage.backend = "postgres"
    errors = startup_preflight_errors(cfg)
    assert not any("Dual data stack requires" in e for e in errors)


def test_dual_data_stack_can_be_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "true")
    monkeypatch.setenv("ARQONBUS_REQUIRE_DUAL_DATA_STACK", "false")
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.delenv("ARQONBUS_REDIS_URL", raising=False)
    monkeypatch.delenv("ARQONBUS_VALKEY_URL", raising=False)
    monkeypatch.setenv("ARQONBUS_POSTGRES_URL", "postgresql://127.0.0.1:5432/arqonbus")

    cfg = ArqonBusConfig()
    cfg.environment = "prod"
    cfg.storage.mode = "strict"
    cfg.storage.backend = "postgres"
    errors = startup_preflight_errors(cfg)
    assert not any("Dual data stack requires ARQONBUS_VALKEY_URL" in e for e in errors)


def test_startup_preflight_non_strict_allows_defaults(monkeypatch):
    monkeypatch.setenv("ARQONBUS_PREFLIGHT_STRICT", "false")
    cfg = ArqonBusConfig()
    cfg.environment = "dev"

    assert startup_preflight_errors(cfg) == []


def test_prod_preflight_rejects_jwt_skip_validation_toggle(monkeypatch):
    monkeypatch.delenv("ARQONBUS_PREFLIGHT_STRICT", raising=False)
    monkeypatch.setenv("JWT_SKIP_VALIDATION", "1")
    monkeypatch.setenv("ARQONBUS_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("ARQONBUS_SERVER_PORT", "9100")
    monkeypatch.setenv("ARQONBUS_STORAGE_MODE", "strict")
    monkeypatch.setenv("ARQONBUS_VALKEY_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("ARQONBUS_POSTGRES_URL", "postgresql://127.0.0.1:5432/arqonbus")

    cfg = ArqonBusConfig()
    cfg.environment = "prod"
    cfg.storage.mode = "strict"
    cfg.storage.backend = "postgres"
    errors = startup_preflight_errors(cfg)
    assert any("JWT_SKIP_VALIDATION is forbidden" in e for e in errors)


def test_environment_name_normalization_accepts_profile_aliases():
    assert normalize_environment_name("development") == "dev"
    assert normalize_environment_name("DEV") == "dev"
    assert normalize_environment_name("staging") == "staging"
    assert normalize_environment_name("production") == "prod"
    assert normalize_environment_name("prod") == "prod"


def test_environment_name_normalization_rejects_unknown_profile():
    with pytest.raises(ValueError, match="Unsupported environment profile"):
        normalize_environment_name("test")


def test_staging_profile_enables_strict_preflight_without_flag(monkeypatch):
    monkeypatch.delenv("ARQONBUS_PREFLIGHT_STRICT", raising=False)
    monkeypatch.delenv("ARQONBUS_SERVER_HOST", raising=False)
    monkeypatch.delenv("ARQONBUS_SERVER_PORT", raising=False)
    monkeypatch.delenv("ARQONBUS_STORAGE_MODE", raising=False)

    cfg = ArqonBusConfig()
    cfg.environment = "staging"
    errors = startup_preflight_errors(cfg)
    assert any("ARQONBUS_SERVER_HOST" in e for e in errors)
    assert any("ARQONBUS_SERVER_PORT" in e for e in errors)
    assert any("ARQONBUS_STORAGE_MODE" in e for e in errors)


def test_load_config_respects_environment_variable_when_override_missing(monkeypatch):
    monkeypatch.setenv("ARQONBUS_ENVIRONMENT", "production")
    cfg = load_config()
    assert cfg.environment == "prod"
