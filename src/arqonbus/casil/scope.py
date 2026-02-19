"""CASIL scope selection utilities."""

from fnmatch import fnmatch
from typing import Optional

from ..config.config import CASILConfig


def _match_pattern(value: str, pattern: str) -> bool:
    """Check if a value matches a prefix or glob-like pattern."""
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return fnmatch(value, pattern)


def in_scope(room: Optional[str], channel: Optional[str], casil_config: CASILConfig) -> bool:
    """Determine if a message is within CASIL inspection scope."""
    if not casil_config.enabled:
        return False

    target = ""
    if room and channel:
        target = f"{room}:{channel}"
    elif room:
        target = room
    elif channel:
        target = channel

    if not target:
        return False

    if casil_config.scope.exclude and any(_match_pattern(target, pattern) for pattern in casil_config.scope.exclude):
        return False

    if casil_config.scope.include:
        return any(_match_pattern(target, pattern) for pattern in casil_config.scope.include)

    # No include list means inspect all (when enabled)
    return True
