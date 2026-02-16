import unittest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from arqonbus.routing.dispatcher import TaskDispatcher, DispatchStrategy
from arqonbus.routing.operator_registry import OperatorRegistry
from arqonbus.routing.router import MessageRouter
from arqonbus.protocol.envelope import Envelope

class TestDispatchIntegration(unittest.TestCase):
    def setUp(self):
        # Real OperatorRegistry
        self.registry = OperatorRegistry()
        
        # Mock Router (too many dependencies to use real one easily without full server init)
        self.mock_router = MagicMock()
        self.mock_router.route_direct_message = AsyncMock(return_value=True)
        
        self.dispatcher = TaskDispatcher(self.registry, self.mock_router)

    def test_integration_competing(self):
        """Verify dispatcher works with real registry for competing strategy."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. Register 3 operators for a capability
        capability = "code.rust"
        loop.run_until_complete(self.registry.register_operator("op-rust-1", capability))
        loop.run_until_complete(self.registry.register_operator("op-rust-2", capability))
        loop.run_until_complete(self.registry.register_operator("op-rust-3", capability))
        
        # 2. Dispatch task
        task_env = Envelope(type="command", id="task-rust-1")
        
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, capability, strategy=DispatchStrategy.COMPETING)
        )
        
        # 3. Verify
        self.assertEqual(count, 3)
        self.assertEqual(self.mock_router.route_direct_message.call_count, 3)
        
        # Check that it called with the right IDs
        called_ids = [call.kwargs['target_client_id'] for call in self.mock_router.route_direct_message.call_args_list]
        self.assertCountEqual(called_ids, ["op-rust-1", "op-rust-2", "op-rust-3"])
        
        loop.close()

    def test_integration_round_robin_group_isolation(self):
        """Verify group isolation and single dispatch."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Register operators in different groups
        loop.run_until_complete(self.registry.register_operator("python-1", "code.python"))
        loop.run_until_complete(self.registry.register_operator("rust-1", "code.rust"))
        
        task_env = Envelope(type="command", id="task-py-1")
        
        # Dispatch to python group
        count = loop.run_until_complete(
            self.dispatcher.dispatch_task(task_env, "code.python", strategy=DispatchStrategy.ROUND_ROBIN)
        )
        
        self.assertEqual(count, 1)
        
        # Check that it called correct operator
        called_id = self.mock_router.route_direct_message.call_args.kwargs['target_client_id']
        self.assertEqual(called_id, "python-1")
        
        loop.close()

if __name__ == "__main__":
    unittest.main()
