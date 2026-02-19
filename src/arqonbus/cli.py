"""ArqonBus operator/developer CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .sdk import ArqonBusClient, ArqonBusConnectionError, ArqonBusProtocolError


DEFAULT_HTTP_URL = os.getenv("ARQONBUS_HTTP_URL", "http://127.0.0.1:8080")
DEFAULT_WS_URL = os.getenv("ARQONBUS_WS_URL", "ws://127.0.0.1:9100")


def _parse_header_items(header_items: List[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for item in header_items:
        if ":" not in item:
            raise ValueError(f"Invalid header format '{item}', expected 'Key:Value'")
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid header '{item}': header key cannot be empty")
        parsed[key] = value
    return parsed


def _http_get_json(url: str, timeout_seconds: float) -> Dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError(f"Expected JSON object from {url}")
            return data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {exc}") from exc


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _format_tail_message(message: Dict[str, Any], raw: bool) -> str:
    if raw:
        return json.dumps(message, sort_keys=True)

    timestamp = message.get("timestamp", "")
    message_type = message.get("type", "")
    sender = message.get("sender", "")
    room = message.get("room", "")
    channel = message.get("channel", "")
    payload = json.dumps(message.get("payload", {}), sort_keys=True)
    return (
        f"{timestamp} type={message_type} sender={sender} "
        f"room={room} channel={channel} payload={payload}"
    )


async def _run_tail_command(args: argparse.Namespace) -> int:
    headers = _parse_header_items(args.header)
    async with ArqonBusClient(
        args.ws_url,
        jwt_token=args.jwt,
        headers=headers,
        connect_timeout=args.timeout_seconds,
    ) as client:
        if args.send is not None:
            send_payload = json.loads(args.send)
            if not isinstance(send_payload, dict):
                raise ValueError("--send payload must be a JSON object")
            await client.send_json(send_payload)

        for _ in range(args.limit):
            message = await client.recv_json(timeout=args.timeout_seconds)
            print(_format_tail_message(message, raw=args.raw))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arqon", description="ArqonBus CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Fetch /status from ArqonBus HTTP server")
    status_parser.add_argument("--http-url", default=DEFAULT_HTTP_URL, help="Base HTTP URL")
    status_parser.add_argument("--timeout-seconds", type=float, default=5.0, help="HTTP timeout")

    version_parser = subparsers.add_parser(
        "version",
        help="Fetch /version from ArqonBus HTTP server",
    )
    version_parser.add_argument("--http-url", default=DEFAULT_HTTP_URL, help="Base HTTP URL")
    version_parser.add_argument("--timeout-seconds", type=float, default=5.0, help="HTTP timeout")

    tail_parser = subparsers.add_parser("tail", help="Open WebSocket and print inbound envelopes")
    tail_parser.add_argument("--ws-url", default=DEFAULT_WS_URL, help="WebSocket URL")
    tail_parser.add_argument(
        "--jwt",
        default=os.getenv("ARQONBUS_AUTH_JWT"),
        help="Bearer JWT token",
    )
    tail_parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="KEY:VALUE",
        help="Additional request header (repeatable)",
    )
    tail_parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of received messages before exiting",
    )
    tail_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Connection and receive timeout",
    )
    tail_parser.add_argument(
        "--send",
        default=None,
        help="Optional JSON object to send immediately after connect",
    )
    tail_parser.add_argument(
        "--raw",
        action="store_true",
        help="Print each message as compact raw JSON",
    )

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            payload = _http_get_json(f"{args.http_url.rstrip('/')}/status", args.timeout_seconds)
            _print_json(payload)
            return 0

        if args.command == "version":
            payload = _http_get_json(f"{args.http_url.rstrip('/')}/version", args.timeout_seconds)
            _print_json(payload)
            return 0

        if args.command == "tail":
            return asyncio.run(_run_tail_command(args))

        parser.error(f"Unknown command: {args.command}")
        return 2
    except (ValueError, RuntimeError, ArqonBusConnectionError, ArqonBusProtocolError) as exc:
        print(f"arqon: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
