import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from arqonbus.routing.router import RoutingCoordinator
from arqonbus.routing.dispatcher import TaskDispatcher, DispatchStrategy
from arqonbus.protocol.envelope import Envelope

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.open = True

    async def send(self, message):
        self.sent_messages.append(message)

class TestDispatchE2E(unittest.TestCase):
    def setUp(self):
        self.coordinator = RoutingCoordinator()
        self.dispatcher = TaskDispatcher(
            self.coordinator.operator_registry,
            self.coordinator.router
        )

    def test_e2e_parallel_speculation(self):
        """E2E simulation of Parallel Speculation strategy."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. Connect 3 operators
        ops = ["op-1", "op-2", "op-3"]
        websockets = {op: MockWebSocket() for op in ops}
        
        for op_id_label in ops:
            # Add to client registry first (router needs this)
            # websocket must be first
            real_client_id = loop.run_until_complete(
                self.coordinator.client_registry.register_client(websockets[op_id_label])
            )
            # Register as operator in group 'code.patch'
            loop.run_until_complete(
                self.coordinator.operator_registry.register_operator(real_client_id, "code.patch")
            )
            # Map label to real ID for verification
            websockets[op_id_label].real_id = real_client_id
            websockets[real_client_id] = websockets.pop(op_id_label)
            
        real_ops = [ws.real_id for ws in websockets.values()]
        # 2. Dispatch Task
        task_env = Envelope(
            type="command",
            id="task-456",
            sender="user-alpha",
            payload={"action": "refactor_auth"}
        )
        
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, "code.patch", strategy=DispatchStrategy.COMPETING)
        )
        
        # 3. Verify
        self.assertEqual(count, 3)
        for op_id in real_ops:
            ws = websockets[op_id]
            self.assertEqual(len(ws.sent_messages), 1)
            msg = Envelope.from_json(ws.sent_messages[0])
            self.assertEqual(msg.id, "task-456")
            self.assertEqual(msg.payload["action"], "refactor_auth")
            
        loop.close()

if __name__ == "__main__":
    unittest.main()
