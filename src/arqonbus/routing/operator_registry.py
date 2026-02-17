"""Operator registry for ArqonBus task queueing.

Tracks active operators (workers) and their group memberships,
enabling 1:1 task distribution via Redis Streams.
"""
import logging
import asyncio
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OperatorInfo:
    """Metadata for a connected operator."""
    def __init__(self, client_id: str, group: str):
        self.client_id = client_id
        self.group = group
        self.joined_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.tasks_processed = 0

class OperatorRegistry:
    """Manages operator lifecycle and group subscriptions."""
    
    def __init__(self, storage=None):
        self.storage = storage  # MessageStorage instance
        # {group_name: {client_id: OperatorInfo}}
        self.groups: Dict[str, Dict[str, OperatorInfo]] = {}
        # {client_id: group_name}
        self.client_to_group: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def register_operator(self, client_id: str, group: str, auth_token: str = ""):
        """Register a client as an operator for a specific group.
        
        Enforces a simple capability token check to prevent unauthorized 
        operators from joining critical groups.
        """
        # Simple hardcoded check for the audit fix. 
        # In production, this would be a proper secret management system.
        expected_token = "rsi_secret_token_123"
        
        if auth_token != expected_token:
            logger.warning(f"Operator {client_id} failed auth for group {group}")
            return False

        async with self._lock:
            if group not in self.groups:
                self.groups[group] = {}
            
            # Ensure consumer group exists in Redis
            if self.storage:
                stream = f"arqonbus:group:{group}"
                await self.storage.ensure_group(stream, group)

            self.groups[group][client_id] = OperatorInfo(client_id, group)
            self.client_to_group[client_id] = group
            logger.info(f"Operator {client_id} joined group {group} (Authenticated)")
            return True

    async def unregister_operator(self, client_id: str):
        """Clean up operator registration on disconnect."""
        async with self._lock:
            group = self.client_to_group.pop(client_id, None)
            if group:
                if group in self.groups:
                    self.groups[group].pop(client_id, None)
                    if not self.groups[group]:
                        del self.groups[group]
                logger.info(f"Operator {client_id} left group {group}")

    async def get_operators(self, group: str) -> List[str]:
        """Get all active client IDs for a group."""
        async with self._lock:
            group_operators = self.groups.get(group, {})
            return list(group_operators.keys())

    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        async with self._lock:
            group_stats = {}
            for group, ops in self.groups.items():
                group_stats[group] = {
                    "count": len(ops),
                    "operators": list(ops.keys())
                }
            return {
                "total_operators": len(self.client_to_group),
                "groups": group_stats
            }
