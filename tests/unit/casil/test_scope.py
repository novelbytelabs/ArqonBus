import pytest

from arqonbus.config.config import CASILConfig
from arqonbus.casil.scope import in_scope


def test_in_scope_include_match():
    cfg = CASILConfig(enabled=True)
    cfg.scope.include = ["secure-*"]
    assert in_scope("secure-room", "updates", cfg)
    assert not in_scope("public", "chat", cfg)


def test_in_scope_exclude_overrides_include():
    cfg = CASILConfig(enabled=True)
    cfg.scope.include = ["secure-*"]
    cfg.scope.exclude = ["secure-banned*"]
    assert not in_scope("secure-banned", "updates", cfg)


def test_in_scope_all_when_enabled_and_no_includes():
    cfg = CASILConfig(enabled=True)
    assert in_scope("any", "channel", cfg)
