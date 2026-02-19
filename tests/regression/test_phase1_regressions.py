import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.routing.dispatcher import DispatchStrategy, ResultCollector, TaskDispatcher
from arqonbus.routing.operator_registry import OperatorRegistry
from arqonbus.transport.http_server import ArqonBusHTTPServer


@pytest.mark.asyncio
async def test_dispatch_competing_returns_count_by_default():
    registry = MagicMock()
    router = MagicMock()
    registry.get_operators = AsyncMock(return_value=["op1", "op2"])
    router.route_direct_message = AsyncMock(return_value=True)

    collector = ResultCollector()
    dispatcher = TaskDispatcher(registry, router, collector)

    result = await dispatcher.dispatch_task(
        Envelope(type="command", id="task-reg-1"),
        "cap.test",
        strategy=DispatchStrategy.COMPETING,
    )

    assert result == 2
    assert collector.get_future("task-reg-1") is None


@pytest.mark.asyncio
async def test_dispatch_competing_future_is_opt_in():
    registry = MagicMock()
    router = MagicMock()
    registry.get_operators = AsyncMock(return_value=["op1", "op2"])
    router.route_direct_message = AsyncMock(return_value=True)

    collector = ResultCollector()
    dispatcher = TaskDispatcher(registry, router, collector)

    future = await dispatcher.dispatch_task(
        Envelope(type="command", id="task-reg-2"),
        "cap.test",
        strategy=DispatchStrategy.COMPETING,
        return_selection_future=True,
    )

    assert isinstance(future, asyncio.Future)
    assert collector.get_future("task-reg-2") is future

    await collector.add_result("task-reg-2", Envelope(type="response", id="r1"))
    await collector.add_result("task-reg-2", Envelope(type="response", id="r2"))
    results = await asyncio.wait_for(future, timeout=1.0)
    assert len(results) == 2


def test_operator_registry_allows_default_registration_without_auth(monkeypatch):
    monkeypatch.delenv("ARQONBUS_OPERATOR_AUTH_REQUIRED", raising=False)
    monkeypatch.delenv("ARQONBUS_OPERATOR_AUTH_TOKEN", raising=False)

    registry = OperatorRegistry()
    result = asyncio.run(registry.register_operator("op-default", "group.test"))
    assert result is True


def test_operator_registry_enforces_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("ARQONBUS_OPERATOR_AUTH_REQUIRED", "true")
    monkeypatch.setenv("ARQONBUS_OPERATOR_AUTH_TOKEN", "secret-token")

    registry = OperatorRegistry()

    denied = asyncio.run(registry.register_operator("op-denied", "group.test", auth_token="wrong"))
    allowed = asyncio.run(
        registry.register_operator("op-allowed", "group.test", auth_token="secret-token")
    )

    assert denied is False
    assert allowed is True


class _RequestStub:
    def __init__(self, headers):
        self.headers = headers


def test_http_admin_api_key_validation_helper():
    server = ArqonBusHTTPServer(
        {"http_host": "127.0.0.1", "http_port": 8080, "http_enabled": False, "api_key": "k1"}
    )

    assert server._is_admin_request_authorized(_RequestStub({"x-api-key": "k1"})) is True
    assert server._is_admin_request_authorized(_RequestStub({"X-API-Key": "k1"})) is True
    assert server._is_admin_request_authorized(_RequestStub({"x-api-key": "wrong"})) is False
