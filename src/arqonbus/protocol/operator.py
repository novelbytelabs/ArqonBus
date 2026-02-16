from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id

logger = logging.getLogger(__name__)

class ImprovementType(str, Enum):
    """Types of allowable RSI Improvement Operators."""
    PATCH = "patch"           # Modify source code
    TUNE = "tune"             # Tune a hyperparameter
    ADD_TEST = "add_test"     # Add a regression test
    REFACTOR = "refactor"     # Refactor code structure
    PROPOSE = "propose"       # Propose a conceptual change

@dataclass
class Action:
    """The Improvement Operator (A_t).
    
    A mathematically defined operation on the System State.
    """
    type: ImprovementType
    payload: Dict[str, Any]
    description: str
    witness_ref: Optional[str] = None  # SHA-256 of the justification/test pass

@dataclass
class State:
    """The System Snapshot (S_t)."""
    context: Dict[str, Any]
    history: List[Envelope] = field(default_factory=list)

class Operator(ABC):
    """The Recursive Self-Improvement Agent (Tier Omega).
    
    Implements the SAM (State-Action-Model) interface.
    """
    
    def __init__(self, operator_id: str, capabilities: List[str]):
        self.operator_id = operator_id
        self.capabilities = capabilities
        self._state = State(context={})

    @abstractmethod
    async def process(self, state: State) -> Union[Action, List[Action]]:
        """The core SAM loop (M_t).
        
        Args:
            state: The current system state S_t.
            
        Returns:
            The Improvement Operator(s) A_t.
        """
        pass

    async def on_task(self, envelope: Envelope) -> Optional[Envelope]:
        """Adapter from Bus Task to SAM State.
        
        This method hydrates the state from the incoming envelope,
        invokes the process loop, and wraps the result.
        """
        try:
            # 1. Hydrate State (S_t)
            self._hydrate_state(envelope)
            
            # 2. Invoke Model (M_t) -> Action (A_t)
            actions = await self.process(self._state)
            if not isinstance(actions, list):
                actions = [actions]
            
            # 3. Emit Result (to be validated by Tier 2)
            results = []
            for action in actions:
                logger.info(f"Operator {self.operator_id} generated action: {action.type} - {action.description}")
                results.append(action.__dict__)
                
            # Wrap in Envelope
            response = Envelope(
                id=generate_message_id(),
                type="operator_result",
                sender=self.operator_id,
                room=envelope.room,
                channel=envelope.channel,
                payload={"actions": results},
                request_id=envelope.id
            )
            return response

        except Exception as e:
            logger.error(f"Operator {self.operator_id} failed to process task {envelope.id}: {e}")
            # Return error envelope
            return Envelope(
                id=generate_message_id(),
                type="operator_error",
                sender=self.operator_id,
                room=envelope.room,
                channel=envelope.channel,
                payload={"error": str(e)},
                request_id=envelope.id,
                error=str(e)
            )

    def _hydrate_state(self, envelope: Envelope):
        """Update internal state from task envelope."""
        # Simplified hydration
        self._state.context.update(envelope.payload)
        self._state.history.append(envelope)
