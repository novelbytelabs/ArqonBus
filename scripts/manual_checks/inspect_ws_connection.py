import asyncio
import websockets

async def inspect():
    url = "ws://localhost:8081"
    try:
        async with websockets.connect(url) as ws:
            print(f"Connection type: {type(ws)}")
            # print(f"Attributes: {dir(ws)}")
            if hasattr(ws, 'closed'):
                print(f"ws.closed: {ws.closed}")
            else:
                print("ws HAS NO 'closed' attribute")
            
            # Check for protocol or other attributes
            if hasattr(ws, 'protocol'):
                print(f"ws.protocol type: {type(ws.protocol)}")
                if hasattr(ws.protocol, 'state'):
                    print(f"ws.protocol.state: {ws.protocol.state}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
