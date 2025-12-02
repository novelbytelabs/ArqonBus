"""Minimal aiohttp stub for testing without external dependency."""

import asyncio
from types import SimpleNamespace


class _Response:
    def __init__(self, data):
        self._data = data
        self.status = 200

    async def json(self):
        return self._data if isinstance(self._data, dict) else {}

    async def text(self):
        if isinstance(self._data, str):
            return self._data
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class ClientSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        # Return generic healthy payloads
        if "health" in url:
            return _Response({"status": "healthy"})
        if "metrics/prometheus" in url:
            return _Response("arqonbus_metrics 1\n")
        return _Response({"system": "arqonbus"})
