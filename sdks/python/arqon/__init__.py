import nats
import os

async def connect(servers=None):
    """
    Connect to ArqonBus.
    Wraps standard NATS connection with Arqon defaults.
    """
    if not servers:
        servers = os.getenv("NATS_URL", "nats://localhost:4222")
    
    nc = await nats.connect(servers)
    return nc
