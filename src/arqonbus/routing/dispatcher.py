"""Task Dispatcher for ArqonBus Operator Model.

Handles the routing of Improvement Tasks to Operators based on
capabilities and dispatch strategies (e.g., Parallel Speculation).
"""
import logging
import asyncio
import random
from typing import Optional, List, Dict, Any
from enum import Enum

from ..protocol.envelope import Envelope
from ..protocol.ids import generate_message_id
from .operator_registry import OperatorRegistry
from .router import MessageRouter

logger = logging.getLogger(__name__)

class DispatchStrategy(str, Enum):
    """Strategies for dispatching tasks to operators."""
    ROUND_ROBIN = "round_robin"   # Default: Send to one operator (load balanced)
    COMPETING = "competing"       # RSI: Send to all operators (winner takes all)
    BROADCAST = "broadcast"       # Send to all (informational)

class TaskDispatcher:
    """Manages the dispatch of tasks to operators."""

    def __init__(
        self,
        operator_registry: OperatorRegistry,
        message_router: MessageRouter
    ):
        self.operator_registry = operator_registry
        self.message_router = message_router

    async def dispatch_task(
        self,
        task_envelope: Envelope,
        required_capability: str,
        strategy: DispatchStrategy = DispatchStrategy.ROUND_ROBIN
    ) -> int:
        """Dispatch a task to suitable operators.
        
        Args:
            task_envelope: The task to dispatch
            required_capability: The capability group needed (e.g., 'code.python')
            strategy: Dispatch strategy to use
            
        Returns:
            Number of operators the task was sent to.
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
            return sent_count

        except Exception as e:
            logger.error(f"Failed to dispatch task {task_envelope.id}: {e}")
            return 0
