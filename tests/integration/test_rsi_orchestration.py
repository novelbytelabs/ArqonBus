import pytest
import asyncio
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.synthesis_operator import SynthesisOperator
from arqonbus.routing.dispatcher import TaskDispatcher, ResultCollector, DispatchStrategy
from arqonbus.routing.operator_registry import OperatorRegistry
from arqonbus.routing.router import MessageRouter
selection_mod = pytest.importorskip(
    "integriguard.governance.rsi.selection_function",
    reason="Integriguard RSI package not installed",
)
select_winning_action = selection_mod.select_winning_action
pytestmark = [pytest.mark.external, pytest.mark.integration]

@pytest.mark.asyncio
async def test_rsi_parallel_speculation_e2e():
    """End-to-end test for RSI Parallel Speculation (Winner Takes All)."""
    
    # 1. Setup
    registry = OperatorRegistry()
    
    # Mock Router (just captures sent messages)
    class MockRouter:
        def __init__(self):
            self.sent_messages = []
        async def route_direct_message(self, envelope, sender_client_id, target_client_id):
            self.sent_messages.append((envelope, target_client_id))
            return True
            
    router = MockRouter()
    
    # Setup Selection Function bridge
    async def selection_bridge(task_id, results, metadata):
        # Convert Envelope objects back to dicts for the selection function
        result_dicts = [r.to_dict() for r in results]
        return select_winning_action(task_id, result_dicts, metadata)
        
    collector = ResultCollector(selection_callback=selection_bridge, timeout=2.0)
    dispatcher = TaskDispatcher(registry, router, collector)
    
    # 2. Register Operators
    op_speed = SynthesisOperator("op_speed", ["synthesis"])
    op_safety = SynthesisOperator("op_safety", ["synthesis"])
    
    # Register in registry
    await registry.register_operator("op_speed", "synthesis")
    await registry.register_operator("op_safety", "synthesis")
    
    # 3. Dispatch Competing Task
    task = Envelope(type="command", command="rsi.improve", payload={"target": "core.py"})
    
    # This should return a future because we use COMPETING strategy
    selection_future = await dispatcher.dispatch_task(
        task, 
        "synthesis", 
        strategy=DispatchStrategy.COMPETING,
        return_selection_future=True,
    )
    
    assert isinstance(selection_future, asyncio.Future)
    assert len(router.sent_messages) == 2
    
    # 4. Simulate Operator Responses
    # SynthesisOperator.on_task returns an Envelope
    
    # Case A: op_speed returns a speedy but potentially "less safe" improvement
    resp_speed = await op_speed.on_task(task)
    resp_speed.payload["variant"] = "speed"
    
    # Case B: op_safety returns a safe improvement
    resp_safety = await op_safety.on_task(task)
    resp_safety.payload["variant"] = "safety"
    
    # Push results into collector (this is what WebSocketBus would do)
    await collector.add_result(task.id, resp_speed)
    await collector.add_result(task.id, resp_safety)
    
    # 5. Verify Selection
    winning_action = await asyncio.wait_for(selection_future, timeout=1.0)
    
    assert winning_action is not None
    assert winning_action["verdict"] == "PASS"
    assert winning_action["decision"] == "PROMOTE_CANDIDATE"
    
    # In our mock selection function, it uses a deterministic sender-based score.
    # Let's verify that a winner was indeed picked.
    logger_output = winning_action["reason"]
    assert "SUCCESS/OPERATOR" in logger_output
