import unittest
import asyncio
from unittest.mock import MagicMock
from arqonbus.routing.router import RoutingCoordinator
from arqonbus.protocol.envelope import Envelope

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.open = True

    async def send(self, message):
        self.sent_messages.append(message)

class TestLegacyDispatch(unittest.TestCase):
    """Ensure standard routing still works after RSI changes."""
    
    def setUp(self):
        self.coordinator = RoutingCoordinator()

    def test_legacy_broadcast(self):
        """Verify standard room/channel broadcast still works."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 0. Pre-register room and channel
        loop.run_until_complete(self.coordinator.room_manager.create_room(room_id="room1"))
        loop.run_until_complete(self.coordinator.channel_manager.create_channel(room_id="room1", channel_id="chan1"))
        
        # Manually link room and channel for routing validation (managers don't do this automatically)
        room = loop.run_until_complete(self.coordinator.room_manager.get_room("room1"))
        channel = loop.run_until_complete(self.coordinator.channel_manager.get_channel("chan1"))
        room.add_channel(channel)
        
        # 1. Connect and Join clients
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        cid1 = loop.run_until_complete(self.coordinator.client_registry.register_client(ws1))
        cid2 = loop.run_until_complete(self.coordinator.client_registry.register_client(ws2))
        
        loop.run_until_complete(self.coordinator.message_router.join_client_to_room_channel(cid1, "room1", "chan1"))
        loop.run_until_complete(self.coordinator.message_router.join_client_to_room_channel(cid2, "room1", "chan1"))
        
        # 2. Broadcast message
        msg_env = Envelope(
            type="message",
            room="room1",
            channel="chan1",
            sender=cid1,
            payload={"text": "hello"}
        )
        
        # Route via coordinator
        sent_count = loop.run_until_complete(
            self.coordinator.router.route_message(msg_env, cid1)
        )
        
        # 3. Verify
        self.assertEqual(sent_count, 1) # Should only send to cid2
        self.assertEqual(len(ws2.sent_messages), 1)
        self.assertEqual(len(ws1.sent_messages), 0) # Excluded sender
        
        loop.close()

if __name__ == "__main__":
    unittest.main()
