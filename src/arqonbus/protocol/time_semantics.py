"""Time and causal semantics utilities for ArqonBus envelopes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MonotonicSequenceGenerator:
    """Per-domain monotonic sequence generator."""

    _counters: Dict[str, int] = field(default_factory=dict)

    def next(self, domain: str) -> int:
        key = str(domain or "default")
        value = self._counters.get(key, 0) + 1
        self._counters[key] = value
        return value

    def current(self, domain: str) -> int:
        return self._counters.get(str(domain or "default"), 0)


def vector_clock_merge(left: Dict[str, int], right: Dict[str, int]) -> Dict[str, int]:
    merged: Dict[str, int] = {}
    keys = set((left or {}).keys()) | set((right or {}).keys())
    for key in keys:
        merged[key] = max(int((left or {}).get(key, 0)), int((right or {}).get(key, 0)))
    return merged


def vector_clock_compare(left: Dict[str, int], right: Dict[str, int]) -> str:
    """Compare vector clocks.

    Returns one of: `equal`, `before`, `after`, `concurrent`.
    """
    keys = set((left or {}).keys()) | set((right or {}).keys())
    if not keys:
        return "equal"

    left_lt = False
    right_lt = False
    for key in keys:
        l = int((left or {}).get(key, 0))
        r = int((right or {}).get(key, 0))
        if l < r:
            left_lt = True
        elif l > r:
            right_lt = True

    if not left_lt and not right_lt:
        return "equal"
    if left_lt and not right_lt:
        return "before"
    if right_lt and not left_lt:
        return "after"
    return "concurrent"
