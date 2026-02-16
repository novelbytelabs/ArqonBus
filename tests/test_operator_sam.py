import unittest
import asyncio
from typing import List, Union
from datetime import datetime, timezone
from arqonbus.protocol.operator import Operator, Action, ImprovementType, State
from arqonbus.protocol.envelope import Envelope

class MockCoder(Operator):
    """A mock operator that proposes a patch."""
    async def process(self, state: State) -> Union[Action, List[Action]]:
        # Check context
        target_file = state.context.get("target_file")
        if not target_file:
            raise ValueError("No target file specified")
            
        return Action(
            type=ImprovementType.PATCH,
            payload={"file": target_file, "content": "print('Hello World')"},
            description="Add hello world print",
            witness_ref="sha256:mock"
        )

class TestOperatorSAM(unittest.TestCase):
    def setUp(self):
        self.operator = MockCoder(operator_id="test-coder-01", capabilities=["code.patch"])

    def test_sam_loop(self):
        """Verify the SAM loop execution."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. Create Task Envelope
        task_env = Envelope(
            id="task-123",
            type="command",
            sender="user",
            room="dev",
            channel="code",
            payload={"target_file": "main.py"},
            command="truth.verify" # Example command
        )
        
        # 2. Run Operator
        result_env = loop.run_until_complete(self.operator.on_task(task_env))
        
        # 3. Verify Result
        self.assertIsNotNone(result_env)
        self.assertEqual(result_env.type, "operator_result")
        self.assertEqual(result_env.sender, "test-coder-01")
        self.assertEqual(result_env.request_id, "task-123")
        
        actions = result_env.payload["actions"]
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["type"], ImprovementType.PATCH)
        self.assertEqual(action["description"], "Add hello world print")
        
        loop.close()

if __name__ == "__main__":
    unittest.main()
