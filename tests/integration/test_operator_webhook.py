import json
import queue
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.socket]

_REQUEST_QUEUE = queue.Queue()


class _WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        _REQUEST_QUEUE.put(json.loads(body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, fmt, *args):
        return


@contextmanager
def _webhook_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/hook"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.asyncio
async def test_registered_webhook_receives_room_channel_message():
    config = ArqonBusConfig()
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "user"}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)

    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)

    with _webhook_server() as webhook_url:
        register_cmd = Envelope(
            id=generate_message_id(),
            type="command",
            command="op.webhook.register",
            args={"url": webhook_url, "room": "science", "channel": "general"},
            payload={},
        )
        await bus._handle_command(register_cmd, "client-1")

        msg = Envelope(
            id=generate_message_id(),
            type="message",
            room="science",
            channel="general",
            payload={"content": "hello-hook"},
        )
        await bus._handle_message(msg, client_id="sender-1")

        webhook_payload = _REQUEST_QUEUE.get(timeout=2)
        assert webhook_payload["sender_client_id"] == "sender-1"
        assert webhook_payload["envelope"]["payload"]["content"] == "hello-hook"
