"""Live RSI Integration Test (Mocking Lattice with Local Subprocess).

This script demonstrates a 'Live' RSI loop where:
1. An OracleOperator is registered with ArqonBus.
2. It uses the real `OracleAdapter` to execute a subprocess (simulating Lattice).
3. The result is returned via the Bus, collected, and selected.
"""
import asyncio
import sys
import logging
from arqonbus.protocol.envelope import Envelope
from arqonbus.routing.dispatcher import TaskDispatcher, ResultCollector, DispatchStrategy
from arqonbus.routing.operator_registry import OperatorRegistry
from arqonbus.routing.router import MessageRouter
from integriguard.governance.rsi.selection_function import select_winning_action
from integriguard.lattice_integration.adapters.oracle_client import OracleOperator
from integriguard.truthloop.oracle.adapter import OracleAdapterConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LIVE_RSI_TEST")

async def run_live_test():
    # 1. Setup Infrastructure
    registry = OperatorRegistry()
    
    class MockRouter:
        def __init__(self):
            self.sent_messages = []
        async def route_direct_message(self, envelope, sender_client_id, target_client_id):
            self.sent_messages.append(envelope)
            return True
            
    router = MockRouter()
    
    async def selection_bridge(task_id, results, metadata):
        result_dicts = [r.to_dict() for r in results]
        return select_winning_action(task_id, result_dicts, metadata)
        
    collector = ResultCollector(selection_callback=selection_bridge, timeout=5.0)
    dispatcher = TaskDispatcher(registry, router, collector)
    
    # 2. Configure Oracle Operator (Simulating Lattice)
    # We will use 'echo' as our "Lattice Sandbox" for this proof of concept.
    # In a real scenario, bin_path would be 'firecracker' or the lattice runtime CLI.
    config = OracleAdapterConfig(
        bin_path="echo", 
        base_args=[],
        strict_arg="VERDICT: PASS" # Mocking the output
    )
    
    oracle_op = OracleOperator("oracle_1", ["verification"], config)
    await registry.register_operator("oracle_1", "verification")
    
    # 3. Dispatch Verification Task
    # The payload 'content' is piped to stdin of the binary.
    # We want 'echo' to verify something. But echo just echoes arguments or stdin?
    # Wait, subprocess.run with input=content writes to stdin. 
    # 'echo' ignores stdin usually. 'cat' would be better.
    
    # Let's use python as the binary to actually execute logic!
    config_python = OracleAdapterConfig(
        bin_path=sys.executable,
        base_args=["-c"],
        strict_arg="print('VERDICT: PASS') if 1+1==2 else print('VERDICT: FAIL')"
    )
    
    real_oracle = OracleOperator("real_python_oracle", ["verification"], config_python)
    await registry.register_operator("real_python_oracle", "verification")
    
    task = Envelope(
        type="verification.request", 
        payload={"content": "", "strict": True} # Content ignored by our -c script
    )
    
    logger.info("Dispatching live verification task...")
    
    # We use COMPETING strategy even for 1 operator to test the collector loop
    future = await dispatcher.dispatch_task(
        task, 
        "verification", 
        strategy=DispatchStrategy.COMPETING
    )
    
    # 4. Operator Processing (Simulated Event Loop)
    logger.info("Operator processing...")
    response = await real_oracle.on_task(task)
    
    # OracleOperator returns type="verification.result", we need to adapt it 
    # or ensure specific fields for the Collector if needed.
    # The ResultCollector expects an Envelope.
    
    logger.info(f"Oracle Response: {response.payload}")
    
    # We need to manually add status='success' for the Selection Function 
    # because OracleOperator might not set it (it's older code).
    response.status = "success" 
    
    await collector.add_result(task.id, response)
    
    # 5. Await Result
    winner = await future
    logger.info(f"Winner Selected: {winner}")
    
    if winner and winner.get("verdict") == "PASS":
        print("\nSUCCESS: Live RSI loop verified with actual subprocess execution!")
    else:
        print("\nFAILURE: Winner not selected or verdict failed.")

if __name__ == "__main__":
    asyncio.run(run_live_test())
