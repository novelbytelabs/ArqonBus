from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.interface import HistoryEntry, StorageBackend, StorageRegistry, StorageResult


class _FactoryBackend(StorageBackend):
    def __init__(self, mode: str = 'ctor'):
        self.mode = mode

    @classmethod
    async def create(cls, config: Dict[str, Any]):
        return cls(mode=f"factory:{config.get('sentinel', 'none')}")

    async def append(self, envelope: Envelope, **kwargs) -> StorageResult:
        return StorageResult(success=True, message_id=envelope.id, timestamp=datetime.utcnow())

    async def get_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[HistoryEntry]:
        return []

    async def delete_message(self, message_id: str) -> StorageResult:
        return StorageResult(success=True, message_id=message_id, timestamp=datetime.utcnow())

    async def clear_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> StorageResult:
        return StorageResult(success=True, timestamp=datetime.utcnow())

    async def get_stats(self) -> Dict[str, Any]:
        return {'mode': self.mode}

    async def health_check(self) -> bool:
        return True

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_storage_registry_prefers_async_factory_when_available():
    name = 'factory_backend_test'
    StorageRegistry.register(name, _FactoryBackend)
    try:
        backend = await StorageRegistry.create_backend(name, sentinel='ok')
        assert isinstance(backend, _FactoryBackend)
        assert backend.mode == 'factory:ok'
    finally:
        StorageRegistry._backends.pop(name, None)
