# Configuration Guide (including CASIL)

## Precedence
1. Environment variables (`ARQONBUS_*`)
2. Config file (if loaded)
3. Defaults (see below)

## Core Defaults (unchanged)
- Server: host `127.0.0.1`, port `8765`, max_connections `1000`
- WebSocket: max_message_size `1MB`, compression `true`
- Storage: backend `memory`, max_history_size `10000`, enable_persistence `false`
- Telemetry: enable `true`, telemetry_room `arqonbus.telemetry`

## CASIL Defaults & Recommended Bounds
- `casil.enabled=false` (opt-in)
- `casil.mode=monitor` (monitor-only; no blocking)
- `casil.default_decision=allow` (fail-open on internal errors)
- `casil.scope.include/exclude=[]` (empty include means inspect all when enabled)
- `casil.limits.max_inspect_bytes=65536` (recommended upper bound: 262144)
- `casil.limits.max_patterns=32` (recommended upper bound: 64)
- `casil.policies.max_payload_bytes=262144` (tighten for sensitive channels)
- `casil.policies.block_on_probable_secret=false` (set true for enforce during incidents)
- `casil.policies.redaction.paths=["password","token","secret"]`
- `casil.policies.redaction.patterns=[]` (add bounded regex/patterns)
- `casil.policies.redaction.never_log_payload_for=[]` (patterns of channels to fully mask in logs/telemetry)
- `casil.policies.redaction.transport_redaction=false` (redact forwarded payloads only when explicitly enabled)
- Metadata exposure: `casil.metadata.to_logs=true`, `casil.metadata.to_telemetry=true`, `casil.metadata.to_envelope=false`

## Recommended Hardened Settings (Incident)
- `ARQONBUS_CASIL_ENABLED=true`
- `ARQONBUS_CASIL_MODE=enforce`
- `ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true`
- `ARQONBUS_CASIL_MAX_PAYLOAD_BYTES` lowered per channel sensitivity
- `ARQONBUS_CASIL_REDACTION_PATTERNS` includes token/secret/API-key shapes
- `ARQONBUS_CASIL_DEFAULT_DECISION=block` (optional for fail-closed)
