import asyncio
import json
import websockets
import time
import uuid

URI = "ws://127.0.0.1:9100"

def generate_valid_message_id():
    timestamp = time.time_ns()
    counter = 1
    uuid_short = uuid.uuid4().hex[:6]
    return f"arq_{timestamp}_{counter}_{uuid_short}"

async def main():
    async with websockets.connect(URI) as ws:
        welcome = await ws.recv()
        print("WELCOME FROM SERVER:", welcome)

        msg = {
            "id": generate_valid_message_id(),
            "type": "message",
            "version": "1.0",
            "room": "secure-payments",
            "channel": "alerts",
            "payload": {"content": "leaked api_key=sk-demo-123456"},
            "args": {},
            "metadata": {}
        }

        print("SENDING MESSAGE:", msg)
        await ws.send(json.dumps(msg))

        reply = await ws.recv()
        print("SERVER REPLY:", reply)

asyncio.run(main())
