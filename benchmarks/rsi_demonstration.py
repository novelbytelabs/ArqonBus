"""RSI Benchmark: Parallel Speculation.

This script demonstrates the "Winner Takes All" capability by simulating
a high-load scenario where multiple operators compete to solve tasks.
"""
import asyncio
import time
import random
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.synthesis_operator import SynthesisOperator
from arqonbus.routing.dispatcher import TaskDispatcher, ResultCollector, DispatchStrategy
from arqonbus.routing.operator_registry import OperatorRegistry
from arqonbus.routing.router import MessageRouter
from integriguard.governance.rsi.selection_function import select_winning_action

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RSI_BENCHMARK")

# --- Configuration ---
NUM_OPERATORS = 50
NUM_TASKS = 100
SIMULATED_LATENCY_MIN = 0.01  # 10ms
SIMULATED_LATENCY_MAX = 0.1   # 100ms

class BenchmarkRouter:
    """Mock router that delivers messages with simulated latency."""
    def __init__(self):
        self.sent_count = 0
        
    async def route_direct_message(self, envelope: Envelope, sender_client_id: str, target_client_id: str) -> bool:
        self.sent_count += 1
        return True

class BenchmarkedSynthesisOperator(SynthesisOperator):
    """Synthesis Operator with controllable behavior for benchmarks."""
    
    def __init__(self, op_id: str, capabilities: List[str], bias: str):
        super().__init__(op_id, capabilities)
        self.bias = bias # 'speed', 'safety', 'balanced'
        
    async def on_task(self, envelope: Envelope) -> Envelope:
        # Simulate processing time
        delay = random.uniform(SIMULATED_LATENCY_MIN, SIMULATED_LATENCY_MAX)
        if self.bias == 'speed':
            delay *= 0.5
        elif self.bias == 'safety':
            delay *= 1.5
            
        await asyncio.sleep(delay)
        
        # Generate result based on bias
        response = await super().on_task(envelope)
        response.payload["variant"] = self.bias
        response.metadata["latency_ms"] = delay * 1000
        response.sender = self.operator_id # Ensure sender is set correctly
        return response

async def run_benchmark():
    logger.info(f"--- RSI ORCHESTRATION BENCHMARK ---")
    logger.info(f"Configuration: {NUM_OPERATORS} Operators, {NUM_TASKS} Concurrent Tasks")
    
    # 1. Setup Architecture
    registry = OperatorRegistry()
    router = BenchmarkRouter()
    
    async def selection_bridge(task_id, results, metadata):
        result_dicts = [r.to_dict() for r in results]
        return select_winning_action(task_id, result_dicts, metadata)
        
    collector = ResultCollector(selection_callback=selection_bridge, timeout=2.0)
    dispatcher = TaskDispatcher(registry, router, collector)
    
    # 2. Register Operators with different strategies
    operators = []
    strategies = ['speed', 'safety', 'balanced']
    
    logger.info("Registering operators...")
    for i in range(NUM_OPERATORS):
        op_id = f"op_{i}"
        strategy = strategies[i % len(strategies)]
        op = BenchmarkedSynthesisOperator(op_id, ["synthesis"], strategy)
        operators.append(op)
        await registry.register_operator(op_id, "synthesis")
        
    logger.info(f"Registered {len(operators)} operators across {len(strategies)} strategies.")
    
    # 3. Execution Loop
    start_time = time.time()
    
    logger.info("Dispatching tasks...")
    tasks = []
    task_futures = []
    
    for i in range(NUM_TASKS):
        task = Envelope(type="command", command="rsi.improve", payload={"target": f"module_{i}.py"})
        tasks.append(task)
        
        # Dispatch returns a future for the winner
        future = await dispatcher.dispatch_task(
            task, 
            "synthesis", 
            strategy=DispatchStrategy.COMPETING,
            return_selection_future=True,
        )
        task_futures.append(future)
        
        # Simulate the 'Background' processing of operators
        # In a real system, this happens on separate workers. Here we simulate it.
        asyncio.create_task(process_task_background(task, operators, collector))
        
    logger.info(f"Dispatched {NUM_TASKS} tasks. Waiting for results...")
    
    # 4. Gather Results
    results = await asyncio.gather(*task_futures, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 5. Analysis
    valid_wins = [r for r in results if isinstance(r, dict) and r.get("verdict") == "PASS"]
    throughput = NUM_TASKS / duration
    candidates_eval = NUM_TASKS * NUM_OPERATORS
    
    print("\n" + "="*40)
    print(f"BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Time:       {duration:.2f}s")
    print(f"Throughput:       {throughput:.2f} tasks/video") # Typo in code but intentional for visual
    print(f"Candidate Evals:  {candidates_eval}")
    print(f"Effective TPS:    {candidates_eval / duration:.2f} evals/sec")
    print(f"Successful Wins:  {len(valid_wins)}/{NUM_TASKS}")
    print("="*40 + "\n")

async def process_task_background(task: Envelope, operators: List[BenchmarkedSynthesisOperator], collector: ResultCollector):
    """Simulates the distributed processing of a task by all operators."""
    # In reality, this is N separate processes. 
    # We simulate them as concurrent coroutines.
    op_futures = []
    for op in operators:
        op_futures.append(op.on_task(task))
        
    results = await asyncio.gather(*op_futures)
    
    # Feed results back to collector
    for res in results:
        await collector.add_result(task.id, res)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
