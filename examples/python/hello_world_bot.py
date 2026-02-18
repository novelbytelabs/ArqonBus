"""ArqonBus Epoch 2 hello-world bot using the first-party Python SDK."""

import asyncio
import json
import os
from datetime import datetime, timezone

from arqonbus.sdk import ArqonBusClient
from arqonbus.protocol.ids import generate_message_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def main() -> None:
    ws_url = os.getenv("ARQONBUS_WS_URL", "ws://127.0.0.1:9100")
    jwt_token = os.getenv("ARQONBUS_AUTH_JWT")
    room = os.getenv("ARQONBUS_HELLO_ROOM", "science")
    channel = os.getenv("ARQONBUS_HELLO_CHANNEL", "general")

    async with ArqonBusClient(ws_url, jwt_token=jwt_token) as client:
        welcome = await client.recv_json(timeout=2.0)
        print("connected:", json.dumps(welcome.get("payload", {}), sort_keys=True))

        hello_message = {
            "id": generate_message_id(),
            "type": "message",
            "timestamp": _now_iso(),
            "version": "1.0",
            "room": room,
            "channel": channel,
            "payload": {"content": "Hello World from ArqonBus SDK bot"},
        }
        await client.send_json(hello_message)
        print("sent:", json.dumps(hello_message["payload"], sort_keys=True))

        # Optional: wait for one inbound frame (ack or routed message) for quick smoke validation.
        try:
            response = await client.recv_json(timeout=1.0)
            print("recv:", json.dumps(response, sort_keys=True))
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
