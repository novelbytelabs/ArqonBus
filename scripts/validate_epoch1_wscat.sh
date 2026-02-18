#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${ARQONBUS_WSCAT_HOST:-127.0.0.1}"
PORT="${ARQONBUS_WSCAT_PORT:-47001}"
SECRET="${ARQONBUS_WSCAT_SECRET:-epoch1-secret}"
WSCAT_BIN="${WSCAT_BIN:-/home/irbsurfer/.nvm/versions/node/v22.20.0/bin/wscat}"

SERVER_LOG="/tmp/arqonbus_epoch1_wscat_server.log"

if [[ ! -x "$WSCAT_BIN" ]]; then
  echo "wscat binary not found or not executable: $WSCAT_BIN" >&2
  exit 1
fi

ARQONBUS_WSCAT_HOST="$HOST" ARQONBUS_WSCAT_PORT="$PORT" ARQONBUS_WSCAT_SECRET="$SECRET" PYTHONPATH=src python - <<'PY' > "$SERVER_LOG" 2>&1 &
import asyncio
import os
import signal

from arqonbus.config.config import ArqonBusConfig
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.transport.websocket_bus import WebSocketBus

HOST = os.getenv("ARQONBUS_WSCAT_HOST", "127.0.0.1")
PORT = int(os.getenv("ARQONBUS_WSCAT_PORT", "47001"))
SECRET = os.getenv("ARQONBUS_WSCAT_SECRET", "epoch1-secret")

stop_event = asyncio.Event()


def _stop(*_args):
    stop_event.set()


async def main() -> None:
    cfg = ArqonBusConfig()
    cfg.server.host = HOST
    cfg.websocket.port = PORT
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = SECRET
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = False

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    print("EPOCH1_WSCAT_SERVER_READY", flush=True)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _stop)
    await stop_event.wait()
    await bus.stop_server()


asyncio.run(main())
PY
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if grep -q "EPOCH1_WSCAT_SERVER_READY" "$SERVER_LOG"; then
    break
  fi
  sleep 0.2
done

if ! grep -q "EPOCH1_WSCAT_SERVER_READY" "$SERVER_LOG"; then
  echo "server failed to become ready" >&2
  sed -n '1,120p' "$SERVER_LOG" >&2
  exit 1
fi

TOKEN="$(ARQONBUS_WSCAT_SECRET="$SECRET" PYTHONPATH=src python - <<'PY'
import os
import time
from arqonbus.security.jwt_auth import issue_hs256_token

now = int(time.time())
print(issue_hs256_token(
    {"sub": "wscat-client", "role": "user", "tenant_id": "tenant-a", "exp": now + 120},
    os.getenv("ARQONBUS_WSCAT_SECRET", "epoch1-secret"),
))
PY
)"

MESSAGE_ID="$(PYTHONPATH=src python - <<'PY'
from arqonbus.protocol.ids import generate_message_id
print(generate_message_id())
PY
)"

set +e
UNAUTH_RAW="$(script -qec "$WSCAT_BIN --no-color -c ws://$HOST:$PORT -w 1" /dev/null 2>&1)"
UNAUTH_RC=$?
AUTH_RAW="$(
  script -qec "$WSCAT_BIN --no-color -H 'Authorization: Bearer $TOKEN' -c ws://$HOST:$PORT -x '{\"id\":\"$MESSAGE_ID\",\"type\":\"command\",\"timestamp\":\"2026-02-18T00:00:00+00:00\",\"version\":\"1.0\",\"command\":\"ping\",\"payload\":{},\"args\":{}}' -w 1" /dev/null 2>&1
)"
AUTH_RC=$?
set -e

UNAUTH_CLEAN="$(printf '%s' "$UNAUTH_RAW" | sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g')"
AUTH_CLEAN="$(printf '%s' "$AUTH_RAW" | sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g')"

echo "UNAUTH_RC=$UNAUTH_RC"
echo "$UNAUTH_CLEAN"
echo "AUTH_RC=$AUTH_RC"
echo "$AUTH_CLEAN"

if ! printf '%s' "$UNAUTH_CLEAN" | grep -q "Unexpected server response: 401"; then
  echo "expected unauthorized 401 handshake evidence not found" >&2
  exit 1
fi

if ! printf '%s' "$AUTH_CLEAN" | grep -q "Connected"; then
  echo "expected authenticated connection evidence not found" >&2
  exit 1
fi

if ! printf '%s' "$AUTH_CLEAN" | grep -q "Connected to ArqonBus"; then
  echo "expected welcome payload evidence not found" >&2
  exit 1
fi

echo "Epoch 1 wscat handshake validation succeeded."
