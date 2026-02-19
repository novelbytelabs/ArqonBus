import json

import pytest

from arqonbus.sdk import ArqonBusClient, ArqonBusConnectionError


class _FakeWebSocket:
    def __init__(self):
        self.closed = False
        self.sent = []
        self.to_recv = [json.dumps({"type": "message", "payload": {"welcome": "Connected"}})]

    async def recv(self):
        return self.to_recv.pop(0)

    async def send(self, payload: str):
        self.sent.append(payload)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_sdk_client_connect_uses_headers_and_jwt(monkeypatch):
    seen = {}
    fake_ws = _FakeWebSocket()

    async def _fake_connect(url, additional_headers, open_timeout):
        seen["url"] = url
        seen["headers"] = dict(additional_headers)
        seen["timeout"] = open_timeout
        return fake_ws

    monkeypatch.setattr("arqonbus.sdk.client.websockets.connect", _fake_connect)

    client = ArqonBusClient(
        "ws://127.0.0.1:9100",
        jwt_token="token-abc",
        headers={"X-Tenant": "tenant-a"},
        connect_timeout=3.0,
    )

    await client.connect()
    assert seen["url"] == "ws://127.0.0.1:9100"
    assert seen["headers"]["Authorization"] == "Bearer token-abc"
    assert seen["headers"]["X-Tenant"] == "tenant-a"
    assert seen["timeout"] == 3.0

    msg = await client.recv_json(timeout=1.0)
    assert msg["payload"]["welcome"] == "Connected"

    await client.send_json({"type": "message", "payload": {"content": "hello"}})
    assert json.loads(fake_ws.sent[0])["payload"]["content"] == "hello"

    await client.close()
    assert fake_ws.closed is True


@pytest.mark.asyncio
async def test_sdk_client_recv_requires_connection():
    client = ArqonBusClient("ws://127.0.0.1:9100")
    with pytest.raises(ArqonBusConnectionError, match="not connected"):
        await client.recv_json(timeout=0.1)
