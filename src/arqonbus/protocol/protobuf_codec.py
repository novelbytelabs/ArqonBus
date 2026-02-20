"""Protobuf codec for ArqonBus infrastructure envelopes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from google.protobuf import json_format
from google.protobuf.struct_pb2 import Struct

from ..proto import bus_payload_pb2, envelope_pb2
from .envelope import Envelope


def _struct_from_dict(data: Dict[str, Any]) -> Struct:
    struct_msg = Struct()
    json_format.ParseDict(data or {}, struct_msg)
    return struct_msg


def _dict_from_struct(struct_msg: Struct) -> Dict[str, Any]:
    if not struct_msg.fields:
        return {}
    value = json_format.MessageToDict(struct_msg)
    return value if isinstance(value, dict) else {}


def envelope_to_proto(envelope: Envelope) -> envelope_pb2.Envelope:
    ts = envelope.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    timestamp_ms = int(ts.timestamp() * 1000)

    pb = envelope_pb2.Envelope()
    pb.trace_id = envelope.id
    pb.tenant_id = str(envelope.metadata.get("tenant_id", "") or "")
    pb.room_id = str(envelope.room or "")
    pb.timestamp = timestamp_ms
    pb.twist_id = str(envelope.metadata.get("twist_id", "") or "")

    if envelope.channel:
        pb.headers["channel"] = envelope.channel
    if envelope.sender:
        pb.headers["sender"] = envelope.sender
    if envelope.version:
        pb.headers["version"] = envelope.version
    if envelope.type:
        pb.headers["envelope_type"] = envelope.type
    if envelope.request_id:
        pb.headers["request_id"] = envelope.request_id
    if envelope.status:
        pb.headers["status"] = envelope.status
    if envelope.error:
        pb.headers["error"] = envelope.error
    if envelope.error_code:
        pb.headers["error_code"] = envelope.error_code
    if envelope.from_client:
        pb.headers["from_client"] = envelope.from_client
    if envelope.to_client:
        pb.headers["to_client"] = envelope.to_client

    payload = bus_payload_pb2.BusPayload(
        envelope_id=envelope.id,
        envelope_type=envelope.type,
        version=envelope.version,
        sender=envelope.sender or "",
        channel=envelope.channel or "",
        command=envelope.command or "",
        request_id=envelope.request_id or "",
        status=envelope.status or "",
        error=envelope.error or "",
        error_code=envelope.error_code or "",
        from_client=envelope.from_client or "",
        to_client=envelope.to_client or "",
        payload=_struct_from_dict(envelope.payload or {}),
        args=_struct_from_dict(envelope.args or {}),
        metadata=_struct_from_dict(envelope.metadata or {}),
    )
    payload_bytes = payload.SerializeToString()

    if envelope.type == "command":
        pb.cmd.type = envelope.command or "command"
        pb.cmd.data = payload_bytes
    else:
        pb.event.type = envelope.type or "message"
        pb.event.data = payload_bytes

    return pb


def envelope_from_proto(pb: envelope_pb2.Envelope) -> Envelope:
    payload_bytes = b""
    command_name = None
    envelope_type = pb.headers.get("envelope_type", "")

    if pb.HasField("cmd"):
        payload_bytes = pb.cmd.data
        command_name = pb.cmd.type or None
        if not envelope_type:
            envelope_type = "command"
    elif pb.HasField("event"):
        payload_bytes = pb.event.data
        if not envelope_type:
            envelope_type = pb.event.type or "message"
    elif pb.HasField("signal"):
        if not envelope_type:
            envelope_type = "telemetry"
    else:
        if not envelope_type:
            envelope_type = "message"

    payload_msg = bus_payload_pb2.BusPayload()
    if payload_bytes:
        payload_msg.ParseFromString(payload_bytes)

    timestamp = datetime.fromtimestamp(pb.timestamp / 1000.0, tz=timezone.utc)
    metadata = _dict_from_struct(payload_msg.metadata)
    # Struct numbers are decoded as floats; coerce known integer fields back to int.
    sequence = metadata.get("sequence")
    if isinstance(sequence, float) and sequence.is_integer():
        metadata["sequence"] = int(sequence)
    vector_clock = metadata.get("vector_clock")
    if isinstance(vector_clock, dict):
        normalized_clock: Dict[str, Any] = {}
        for node, counter in vector_clock.items():
            if isinstance(counter, float) and counter.is_integer():
                normalized_clock[str(node)] = int(counter)
            else:
                normalized_clock[str(node)] = counter
        metadata["vector_clock"] = normalized_clock
    if pb.tenant_id:
        metadata.setdefault("tenant_id", pb.tenant_id)
    if pb.twist_id:
        metadata.setdefault("twist_id", pb.twist_id)

    return Envelope(
        id=pb.trace_id or payload_msg.envelope_id,
        timestamp=timestamp,
        type=(payload_msg.envelope_type or envelope_type or "message"),
        version=payload_msg.version or pb.headers.get("version", "1.0"),
        room=pb.room_id or None,
        channel=payload_msg.channel or pb.headers.get("channel") or None,
        sender=payload_msg.sender or pb.headers.get("sender") or None,
        from_client=payload_msg.from_client or pb.headers.get("from_client") or None,
        to_client=payload_msg.to_client or pb.headers.get("to_client") or None,
        payload=_dict_from_struct(payload_msg.payload),
        command=payload_msg.command or command_name,
        args=_dict_from_struct(payload_msg.args),
        request_id=payload_msg.request_id or pb.headers.get("request_id") or None,
        status=payload_msg.status or pb.headers.get("status") or None,
        error=payload_msg.error or pb.headers.get("error") or None,
        error_code=payload_msg.error_code or pb.headers.get("error_code") or None,
        metadata=metadata,
    )


def envelope_to_proto_bytes(envelope: Envelope) -> bytes:
    return envelope_to_proto(envelope).SerializeToString()


def envelope_from_proto_bytes(payload: bytes) -> Envelope:
    pb = envelope_pb2.Envelope()
    pb.ParseFromString(payload)
    return envelope_from_proto(pb)
