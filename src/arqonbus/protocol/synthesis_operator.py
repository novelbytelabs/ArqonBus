"""Tier-Omega synthesis operator for ArqonBus."""
from typing import List, Union
from .operator import Operator, Action, State, ImprovementType

class SynthesisOperator(Operator):
    """Rule-driven synthesis operator (Tier-Omega).

    Produces bounded improvement actions from explicit state signals.
    """

    async def process(self, state: State) -> Union[Action, List[Action]]:
        """Derive an action deterministically from contextual intent and risks."""
        context = state.context or {}
        variant = str(context.get("variant", "default")).strip().lower()
        latency_p99_ms = float(context.get("latency_p99_ms", 0) or 0)
        error_rate = float(context.get("error_rate", 0) or 0)
        target_file = str(context.get("target_file", "core.py")).strip() or "core.py"

        if variant == "safety" or error_rate >= 0.02:
            return Action(
                type=ImprovementType.ADD_TEST,
                payload={
                    "test": "regression_error_budget_guard",
                    "assert": "error_rate < 0.02",
                },
                description="Safety: enforce service error-budget guardrail.",
            )

        if variant == "speed" or latency_p99_ms >= 50.0:
            return Action(
                type=ImprovementType.TUNE,
                payload={
                    "param": "dispatch_batch_size",
                    "direction": "decrease",
                    "reason": "high_p99_latency",
                },
                description="Performance: tune dispatch batch size to reduce p99 latency.",
            )

        return Action(
            type=ImprovementType.REFACTOR,
            payload={
                "file": target_file,
                "goal": "reduce cyclomatic complexity in hot path",
            },
            description="Maintainability: refactor hot-path complexity.",
        )
