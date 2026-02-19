import unittest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from arqonbus.routing.dispatcher import TaskDispatcher, DispatchStrategy
from arqonbus.protocol.envelope import Envelope

class TestTaskDispatcher(unittest.TestCase):
    def setUp(self):
        self.mock_registry = MagicMock()
        self.mock_router = MagicMock()
        self.dispatcher = TaskDispatcher(self.mock_registry, self.mock_router)
        
        # Setup AsyncMocks for registry and router
        self.mock_registry.get_operators = AsyncMock()
        self.mock_router.route_direct_message = AsyncMock()

    def test_dispatch_competing(self):
        """Verify 'competing' strategy sends to all operators."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Mock 3 operators
        self.mock_registry.get_operators.return_value = ["op1", "op2", "op3"]
        self.mock_router.route_direct_message.return_value = True
        
        task_env = Envelope(type="command", id="task-1")
        
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, "code.python", strategy=DispatchStrategy.COMPETING)
        )
        
        self.assertEqual(count, 3)
        self.assertEqual(self.mock_router.route_direct_message.call_count, 3)
        loop.close()

    def test_dispatch_round_robin(self):
        """Verify 'round_robin' strategy sends to only one operator."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Mock 3 operators
        self.mock_registry.get_operators.return_value = ["op1", "op2", "op3"]
        self.mock_router.route_direct_message.return_value = True
        
        task_env = Envelope(type="command", id="task-2")
        
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, "code.python", strategy=DispatchStrategy.ROUND_ROBIN)
        )
        
        self.assertEqual(count, 1)
        self.assertEqual(self.mock_router.route_direct_message.call_count, 1)
        loop.close()

    def test_dispatch_no_operators(self):
        """Verify no messages sent if no operators found."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        self.mock_registry.get_operators.return_value = []
        
        task_env = Envelope(type="command", id="task-3")
        
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, "code.python")
        )
        
        self.assertEqual(count, 0)
        self.assertEqual(self.mock_router.route_direct_message.call_count, 0)
        loop.close()

if __name__ == "__main__":
    unittest.main()
