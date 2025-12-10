# Telemetry Reference (including CASIL)

## Telemetry Transport
- WebSocket telemetry server (configurable via `telemetry` settings).
- Global emitter available via `arqonbus.telemetry.emitter.get_emitter()`.

## CASIL Events

**Event type**: `casil_decision`  
**Payload**:
```json
{
  "event_type": "casil_decision",
  "decision": "ALLOW|ALLOW_WITH_REDACTION|BLOCK",
  "reason_code": "CASIL_POLICY_BLOCKED_SECRET|CASIL_POLICY_OVERSIZE|CASIL_MONITOR_MODE|CASIL_INTERNAL_ERROR",
  "room": "room-name",
  "channel": "channel-name",
  "flags": {
    "contains_probable_secret": true,
    "oversize_payload": true
  },
  "severity": "info|warning",
  "message_id": "<id>",
  "client_id": "<client>"
}
```

### Redaction Rules
- CASIL redaction applies to telemetry snapshots the same as logs (`casil.policies.redaction.*`).
- `never_log_payload_for` patterns mask payload snapshots with `***REDACTED***`.
- Transport-level redaction is opt-in and does not affect telemetry formatting.

### Metrics to Watch
- Inspect count vs allow/redact/block counts
- Reason code breakdown (secrets, oversize)
- Internal error count (should remain zero)
- Hotspot detection by room/channel/client (repeated violations)
