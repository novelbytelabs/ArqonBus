from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.commands.base import CommandContext
from arqonbus.protocol.envelope import Envelope


def _make_context(client_registry):
    return CommandContext(
        client_id="client-1",
        envelope=Envelope(type="command", id="cmd-1"),
        message_router=MagicMock(),
        client_registry=client_registry,
        room_manager=MagicMock(),
        channel_manager=MagicMock(),
        storage=None,
    )


@pytest.mark.asyncio
async def test_check_permission_denies_unknown_client():
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=None)
    ctx = _make_context(registry)
    assert await ctx.check_permission("room_management") is False


@pytest.mark.asyncio
async def test_check_permission_allows_admin_role():
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "admin"}))
    ctx = _make_context(registry)
    assert await ctx.check_permission("channel_management") is True


@pytest.mark.asyncio
async def test_check_permission_allows_when_explicit_permission_present():
    registry = MagicMock()
    registry.get_client = AsyncMock(
        return_value=SimpleNamespace(metadata={"permissions": ["room_management", "status"]})
    )
    ctx = _make_context(registry)
    assert await ctx.check_permission("room_management") is True
    assert await ctx.check_permission("channel_management") is False


@pytest.mark.asyncio
async def test_check_permission_falls_back_to_legacy_allow_without_permissions_field():
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "user"}))
    ctx = _make_context(registry)
    assert await ctx.check_permission("room_management") is True


@pytest.mark.asyncio
async def test_check_permission_rejects_invalid_permissions_type():
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"permissions": "room_management"}))
    ctx = _make_context(registry)
    assert await ctx.check_permission("room_management") is False
