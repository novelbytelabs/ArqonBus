import asyncio
from unittest.mock import AsyncMock

import pytest

from arqonbus.transport.http_server import ArqonBusHTTPServer


class _RequestStub:
    def __init__(self, headers=None):
        self.headers = headers or {}


class _DummyTask:
    done = lambda self: True  # noqa: E731


def _capture_create_task(monkeypatch, bucket):
    def _fake_create_task(coro):
        bucket.append(coro)
        coro.close()
        return _DummyTask()

    monkeypatch.setattr(asyncio, "create_task", _fake_create_task)


@pytest.mark.asyncio
async def test_admin_shutdown_denies_without_api_key():
    server = ArqonBusHTTPServer({"http_enabled": False, "api_key": "secret-key"})
    response = await server.admin_shutdown(_RequestStub(headers={}))
    assert response.status == 401


@pytest.mark.asyncio
async def test_admin_shutdown_authorized_schedules_shutdown(monkeypatch):
    server = ArqonBusHTTPServer({"http_enabled": False, "api_key": "secret-key"})
    server._shutdown_server = AsyncMock()
    scheduled = []
    _capture_create_task(monkeypatch, scheduled)

    response = await server.admin_shutdown(_RequestStub(headers={"x-api-key": "secret-key"}))
    assert response.status == 200
    assert len(scheduled) == 1


@pytest.mark.asyncio
async def test_admin_restart_denies_without_api_key():
    server = ArqonBusHTTPServer({"http_enabled": False, "api_key": "secret-key"})
    response = await server.admin_restart(_RequestStub(headers={}))
    assert response.status == 401


@pytest.mark.asyncio
async def test_admin_restart_authorized_schedules_restart(monkeypatch):
    server = ArqonBusHTTPServer({"http_enabled": False, "api_key": "secret-key"})
    server._restart_server = AsyncMock()
    scheduled = []
    _capture_create_task(monkeypatch, scheduled)

    response = await server.admin_restart(_RequestStub(headers={"X-API-Key": "secret-key"}))
    assert response.status == 200
    assert len(scheduled) == 1
