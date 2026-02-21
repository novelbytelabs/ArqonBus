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

## Continuum Projector Metrics

- `arqonbus_continuum_projector_projection_count`
- `arqonbus_continuum_projector_seen_event_count`
- `arqonbus_continuum_projector_dlq_depth`
- `arqonbus_continuum_projector_events_total{status,event_type,backend}`
- `arqonbus_continuum_projector_event_lag_seconds{event_type}`
- `arqonbus_continuum_projector_dlq_replay_total{replayed,reason,backend}`
- `arqonbus_continuum_projector_backfill_total{dry_run,backend}`
- `arqonbus_continuum_projector_backfill_events_total{outcome}`

Alerting defaults:

- lag p95 > 30s for 5m
- DLQ depth > 100 for 10m
- replay failure ratio > 5% for 15m
