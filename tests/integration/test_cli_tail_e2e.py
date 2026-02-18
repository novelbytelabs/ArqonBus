import argparse
import itertools
import time

import pytest

from arqonbus import cli
from arqonbus.config.config import ArqonBusConfig
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.security.jwt_auth import issue_hs256_token
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(47100)


def _next_port() -> int:
    return next(_port_sequence)


def _make_config(port: int, secret: str) -> ArqonBusConfig:
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = port
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = secret
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = False
    return cfg


@pytest.mark.asyncio
async def test_cli_tail_with_jwt_receives_welcome_message(capsys):
    secret = "epoch2-tail-secret"
    cfg = _make_config(_next_port(), secret)
    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()

    try:
        token = issue_hs256_token(
            {
                "sub": "tail-client",
                "role": "user",
                "tenant_id": "tenant-a",
                "exp": int(time.time()) + 120,
            },
            secret,
        )
        uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"
        parser = cli.build_parser()
        args = parser.parse_args(["tail", "--ws-url", uri, "--jwt", token, "--raw", "--limit", "1"])
        assert isinstance(args, argparse.Namespace)

        rc = await cli._run_tail_command(args)
        assert rc == 0

        output = capsys.readouterr().out
        assert '"welcome": "Connected to ArqonBus"' in output
    finally:
        await bus.stop_server()
