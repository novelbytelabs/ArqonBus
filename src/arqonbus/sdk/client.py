"""Minimal Python SDK client for ArqonBus WebSocket connectivity."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Mapping, Optional

import websockets


class ArqonBusSDKError(Exception):
    """Base SDK error."""


class ArqonBusConnectionError(ArqonBusSDKError):
    """WebSocket connection failed."""


class ArqonBusProtocolError(ArqonBusSDKError):
    """Received invalid protocol payload."""


class ArqonBusClient:
    """Small SDK wrapper around ArqonBus WebSocket transport."""

    def __init__(
        self,
        ws_url: str,
        *,
        jwt_token: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        connect_timeout: float = 5.0,
    ) -> None:
        self.ws_url = ws_url
        self.jwt_token = jwt_token
        self.headers = dict(headers or {})
        self.connect_timeout = connect_timeout
        self._websocket = None

    async def __aenter__(self) -> "ArqonBusClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    def _connection_headers(self) -> Dict[str, str]:
        headers = dict(self.headers)
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers

    async def connect(self) -> None:
        try:
            self._websocket = await websockets.connect(
                self.ws_url,
                additional_headers=self._connection_headers(),
                open_timeout=self.connect_timeout,
            )
        except Exception as exc:
            raise ArqonBusConnectionError(f"Failed to connect to {self.ws_url}: {exc}") from exc

    async def close(self) -> None:
        if self._websocket is None:
            return
        await self._websocket.close()
        self._websocket = None

    async def recv_json(self, *, timeout: Optional[float] = None) -> Dict[str, Any]:
        if self._websocket is None:
            raise ArqonBusConnectionError("Client is not connected")

        try:
            recv_coro = self._websocket.recv()
            raw_message = (
                await asyncio.wait_for(recv_coro, timeout=timeout) if timeout else await recv_coro
            )
            data = json.loads(raw_message)
            if not isinstance(data, dict):
                raise ArqonBusProtocolError("Received non-object JSON payload")
            return data
        except asyncio.TimeoutError as exc:
            raise ArqonBusConnectionError("Timed out waiting for message") from exc
        except json.JSONDecodeError as exc:
            raise ArqonBusProtocolError(f"Invalid JSON payload: {exc}") from exc
        except ArqonBusSDKError:
            raise
        except Exception as exc:
            raise ArqonBusConnectionError(f"Receive failed: {exc}") from exc

    async def send_json(self, message: Mapping[str, Any]) -> None:
        if self._websocket is None:
            raise ArqonBusConnectionError("Client is not connected")
        try:
            await self._websocket.send(json.dumps(dict(message)))
        except Exception as exc:
            raise ArqonBusConnectionError(f"Send failed: {exc}") from exc
