import asyncio
import nats
import websockets
import json

async def test_e2e_shield_nats():
    print(">>> Starting E2E Verification: Shield -> NATS")
    
    # 1. Connect to NATS (The Spine)
    nc = await nats.connect("nats://localhost:4222")
    future = asyncio.Future()

    async def cb(msg):
        print(f"[NATS] Received on {msg.subject}: {msg.data}")
        if msg.data == b"Hello from Shield":
            future.set_result(True)

    # 2. Subscribe to the expected tenant subject
    # Shield logic: "in.t.{tenant_id}.raw". Default tenant is "default".
    await nc.subscribe("in.t.default.raw", cb=cb)
    print(">>> Subscribed to NATS subject: in.t.default.raw")

    # 3. Connect to Shield (The Gateway)
    uri = "ws://localhost:4000/ws"
    async with websockets.connect(uri) as websocket:
        print(f">>> Connected to Shield at {uri}")
        
        # 4. Send Message via WebSocket
        print(">>> Sending 'Hello from Shield' via WebSocket")
        await websocket.send(b"Hello from Shield")

        # 5. Wait for NATS receipt
        try:
            await asyncio.wait_for(future, timeout=5.0)
            print(">>> SUCCESS: Message traversed Shield to NATS!")
        except asyncio.TimeoutError:
            print(">>> FAILURE: NATS did not receive message in 5 seconds.")
            exit(1)

    await nc.close()

if __name__ == "__main__":
    asyncio.run(test_e2e_shield_nats())
