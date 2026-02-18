import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arqonbus import __version__
from arqonbus.transport.http_server import ArqonBusHTTPServer


class _RequestStub:
    headers = {}


@pytest.mark.asyncio
async def test_get_version_reports_package_version():
    server = ArqonBusHTTPServer({"http_enabled": False})
    response = await server.get_version(_RequestStub())
    payload = json.loads(response.text)
    assert response.status == 200
    assert payload["service"] == "arqonbus"
    assert payload["version"] == __version__


def test_setup_routes_registers_version_endpoint():
    server = ArqonBusHTTPServer({"http_enabled": False})
    app = MagicMock()
    app.router = MagicMock()
    server.app = app

    server._setup_routes()

    registered_get_paths = [call.args[0] for call in app.router.add_get.call_args_list]
    assert "/version" in registered_get_paths


@pytest.mark.asyncio
async def test_tracked_handler_records_success_metrics(monkeypatch):
    server = ArqonBusHTTPServer({"http_enabled": False})
    counter_calls = []
    histogram_calls = []

    def _record_counter(*args, **kwargs):
        counter_calls.append((args, kwargs))

    def _record_histogram(*args, **kwargs):
        histogram_calls.append((args, kwargs))

    monkeypatch.setattr("arqonbus.transport.http_server.record_counter", _record_counter)
    monkeypatch.setattr("arqonbus.transport.http_server.record_histogram", _record_histogram)

    async def _ok_handler(_request):
        return SimpleNamespace(status=200)

    wrapped = server._tracked_handler("/health", _ok_handler)
    response = await wrapped(_RequestStub())

    assert response.status == 200
    stats = server._get_request_stats()
    assert stats["total_requests"] == 1
    assert stats["error_count"] == 0
    assert stats["requests_by_endpoint"]["/health"]["count"] == 1
    assert counter_calls[0][0][0] == "http_requests_total"
    assert histogram_calls[0][0][0] == "http_request_duration_seconds"


@pytest.mark.asyncio
async def test_tracked_handler_records_errors(monkeypatch):
    server = ArqonBusHTTPServer({"http_enabled": False})
    counter_calls = []
    histogram_calls = []

    def _record_counter(*args, **kwargs):
        counter_calls.append((args, kwargs))

    def _record_histogram(*args, **kwargs):
        histogram_calls.append((args, kwargs))

    monkeypatch.setattr("arqonbus.transport.http_server.record_counter", _record_counter)
    monkeypatch.setattr("arqonbus.transport.http_server.record_histogram", _record_histogram)

    async def _error_handler(_request):
        return SimpleNamespace(status=503)

    wrapped = server._tracked_handler("/metrics", _error_handler)
    response = await wrapped(_RequestStub())

    assert response.status == 503
    stats = server._get_request_stats()
    assert stats["total_requests"] == 1
    assert stats["error_count"] == 1
    assert stats["requests_by_endpoint"]["/metrics"]["errors"] == 1
    metric_names = [call[0][0] for call in counter_calls]
    assert "http_requests_total" in metric_names
    assert "http_errors_total" in metric_names
    assert histogram_calls[0][0][0] == "http_request_duration_seconds"
