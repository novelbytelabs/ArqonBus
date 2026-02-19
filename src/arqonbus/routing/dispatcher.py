"""Task Dispatcher for ArqonBus Operator Model.

Handles the routing of Improvement Tasks to Operators based on
capabilities and dispatch strategies (e.g., Parallel Speculation).
"""
import logging
import asyncio
import random
from typing import Optional, Any, Dict, List, Union, TYPE_CHECKING
from enum import Enum

from ..protocol.envelope import Envelope
from .operator_registry import OperatorRegistry

if TYPE_CHECKING:
    from .router import MessageRouter

logger = logging.getLogger(__name__)

class DispatchStrategy(str, Enum):
    """Strategies for dispatching tasks to operators."""
    ROUND_ROBIN = "round_robin"   # Default: Send to one operator (load balanced)
    COMPETING = "competing"       # RSI: Send to all operators (winner takes all)
    BROADCAST = "broadcast"       # Send to all (informational)

class ResultCollector:
    """Collects and aggregates results from multiple operators for a single task."""

    def __init__(self, selection_callback: Optional[Any] = None, timeout: float = 5.0):
        self.windows: Dict[str, Dict[str, Any]] = {}  # task_id -> {results, expected, future, timer}
        self.selection_callback = selection_callback
        self.timeout = timeout

    async def open_window(self, task_id: str, expected_count: int, metadata: Optional[Dict[str, Any]] = None):
        """Open a collection window for a task."""
        future: asyncio.Future = asyncio.Future()
        timer = asyncio.create_task(self._timeout_window(task_id))
        
        self.windows[task_id] = {
            "results": [],
            "expected": expected_count,
            "future": future,
            "timer": timer,
            "metadata": metadata or {}
        }
        logger.debug(f"Opened selection window for task {task_id} (expected: {expected_count})")
        return future

    def get_future(self, task_id: str) -> Optional[asyncio.Future]:
        """Get the open selection future for a task if present."""
        window = self.windows.get(task_id)
        if not window:
            return None
        return window.get("future")

    async def add_result(self, task_id: str, result_envelope: Envelope):
        """Add a result to an open window."""
        if task_id not in self.windows:
            logger.warning(f"Received result for unknown task window: {task_id}")
            return

        window = self.windows[task_id]
        window["results"].append(result_envelope)
        
        logger.debug(f"Collected result {len(window['results'])}/{window['expected']} for task {task_id}")

        if len(window["results"]) >= window["expected"]:
            await self._finalize_window(task_id)

    async def _timeout_window(self, task_id: str):
        """Wait for window timeout."""
        await asyncio.sleep(self.timeout)
        if task_id in self.windows:
            logger.info(f"Selection window for task {task_id} timed out after {self.timeout}s")
            await self._finalize_window(task_id)

    async def _finalize_window(self, task_id: str):
        """Finalize the window and trigger selection."""
        window = self.windows.pop(task_id, None)
        if not window:
            return

        # Cancel timeout timer if it's still running
        if not window["timer"].done():
            window["timer"].cancel()

        results = window["results"]
        logger.info(f"Finalized task {task_id} with {len(results)} results")

        # Trigger selection callback if provided
        if self.selection_callback:
            try:
                winner = await self.selection_callback(task_id, results, window["metadata"])
                window["future"].set_result(winner)
            except Exception as e:
                logger.error(f"Selection callback failed for task {task_id}: {e}")
                window["future"].set_exception(e)
        else:
            window["future"].set_result(results)

class TaskDispatcher:
    """Manages the dispatch of tasks to operators."""

    def __init__(
        self,
        operator_registry: OperatorRegistry,
        message_router: "MessageRouter",
        collector: Optional[ResultCollector] = None
    ):
        self.operator_registry = operator_registry
        self.message_router = message_router
        self.collector = collector or ResultCollector()

    async def dispatch_task(
        self,
        task_envelope: Envelope,
        required_capability: str,
        strategy: DispatchStrategy = DispatchStrategy.ROUND_ROBIN,
        return_selection_future: bool = False,
    ) -> Any:
        """Dispatch a task to suitable operators.
        
        Args:
            task_envelope: The task to dispatch
            required_capability: The capability group needed (e.g., 'code.python')
            strategy: Dispatch strategy to use
            return_selection_future: If True with COMPETING strategy, return selection future.
            
        Returns:
            Number of operators the task was sent to by default.
            If `return_selection_future=True` and strategy is COMPETING, returns an asyncio.Future.
        """
        try:
            # 1. Resolve Operators
            # For now, we map 'capability' directly to 'group' in OperatorRegistry
            target_group = required_capability
            
            operators = await self.operator_registry.get_operators(target_group)
            if not operators:
                logger.warning(f"No operators found for capability '{required_capability}'")
                return 0

            # 2. Apply Strategy
            target_operator_ids = []
            
            if strategy == DispatchStrategy.COMPETING or strategy == DispatchStrategy.BROADCAST:
                # Parallel Speculation: Send to ALL operators
                target_operator_ids = operators
            elif strategy == DispatchStrategy.ROUND_ROBIN:
                # Load Balancing: Send to ONE operator (simple random for now)
                # In production, this would use a stateful index in Registry
                target_operator_ids = [random.choice(operators)]
            
            # 3. Route Messages
            sent_count = 0
            
            # If strategy is COMPETING, register with collector BEFORE sending
            selection_future = None
            if (
                strategy == DispatchStrategy.COMPETING
                and self.collector
                and return_selection_future
            ):
                selection_future = await self.collector.open_window(
                    task_envelope.id, 
                    expected_count=len(target_operator_ids),
                    metadata={"capability": required_capability}
                )

            for op_id in target_operator_ids:
                # We route via direct message to target operator ID
                success = await self.message_router.route_direct_message(
                    task_envelope,
                    sender_client_id=task_envelope.sender or "system",
                    target_client_id=op_id
                )
                
                if success:
                    sent_count += 1
            
            logger.info(
                f"Dispatched task {task_envelope.id} to {sent_count} operators "
                f"(Strategy: {strategy}, Capability: {required_capability})"
            )
            
            # Optional: return selection future for RSI workflows.
            if (
                strategy == DispatchStrategy.COMPETING
                and return_selection_future
                and selection_future
            ):
                return selection_future
                
            return sent_count

        except Exception as e:
            logger.error(f"Failed to dispatch task {task_envelope.id}: {e}")
            return 0
