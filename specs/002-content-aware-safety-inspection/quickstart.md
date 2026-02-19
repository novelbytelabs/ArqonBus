# CASIL Quickstart (Monitor vs Enforce)

## Enable CASIL in Monitor Mode (No Blocking)

```bash
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*"
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=65536
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
```

**Behavior**: Messages matching `secure-*` are classified and telemetry is emitted; no blocks occur. Redaction applies to observability targets if configured.

## Enforce Size & Secret Policies

```bash
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*"
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=262144
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_REDACTION_PATTERNS="token,secret,api_key"
export ARQONBUS_CASIL_DEFAULT_DECISION=allow
```

**Behavior**: In-scope messages exceeding `max_payload_bytes` or matching secret patterns are blocked with CASIL reason codes; telemetry/logs record the decision with redaction applied.

## Safe Logging / Telemetry Redaction Only

```bash
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="pii-*"
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=false
```

**Behavior**: Payloads on `pii-*` channels never appear unredacted in logs/telemetry. Transport payloads remain intact unless `ARQONBUS_CASIL_TRANSPORT_REDACTION=true` is set.
