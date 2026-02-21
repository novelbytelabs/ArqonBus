import pytest

from arqonbus.config import config as config_module
from arqonbus.transport import websocket_bus as websocket_bus_module


@pytest.mark.asyncio
async def test_run_server_fails_preflight_in_staging_without_explicit_bind(monkeypatch):
    monkeypatch.setenv("ARQONBUS_ENVIRONMENT", "staging")
    monkeypatch.delenv("ARQONBUS_SERVER_HOST", raising=False)
    monkeypatch.delenv("ARQONBUS_SERVER_PORT", raising=False)
    monkeypatch.delenv("ARQONBUS_STORAGE_MODE", raising=False)
    monkeypatch.setattr(config_module, "_config", None)

    with pytest.raises(RuntimeError, match="Startup preflight failed"):
        await websocket_bus_module.run_server()
