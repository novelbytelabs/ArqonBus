import asyncio
import websockets
import time

async def test_telemetry_bus():
    url = "ws://127.0.0.1:8081"
    print(f"Connecting to telemetry bus at {url}...")
    try:
        async with websockets.connect(url) as ws:
            print("SUCCESS: Connected to telemetry bus.")
            # Keep it open for a bit to check stability
            for i in range(5):
                await asyncio.sleep(1)
                print(f"Connection still open... ({i+1}/5)")
            print("Closing connection...")
    except Exception as e:
        print(f"ERROR: Could not connect to telemetry bus. {e}")

if __name__ == "__main__":
    asyncio.run(test_telemetry_bus())
