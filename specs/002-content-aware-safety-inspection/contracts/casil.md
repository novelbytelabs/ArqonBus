# CASIL Protocol Additions

## Error Codes

- `CASIL_POLICY_BLOCKED_SECRET` – Message blocked due to probable secret detection.
- `CASIL_POLICY_OVERSIZE` – Message blocked for exceeding configured payload limits.
- `CASIL_INTERNAL_ERROR` – CASIL internal error; behavior controlled by `casil.default_decision` (allow/block).
- `CASIL_MONITOR_MODE` – Policies matched but CASIL is in monitor-only mode (informational).

## Envelope Metadata (Optional)

When `casil.metadata.to_envelope=true`, envelopes may include:

```json
{
  "metadata": {
    "casil": {
      "kind": "data|control|telemetry|system|unknown",
      "risk_level": "low|medium|high|unknown",
      "flags": {
        "contains_probable_secret": true,
        "oversize_payload": true
      },
      "reason_code": "CASIL_POLICY_BLOCKED_SECRET",
      "decision": "ALLOW|ALLOW_WITH_REDACTION|BLOCK"
    }
  }
}
```

Clients MAY ignore the `metadata.casil` block; absence implies CASIL disabled or out-of-scope.

## Block Response Shape

```json
{
  "type": "error",
  "request_id": "<original message id>",
  "error": "CASIL blocked message",
  "error_code": "CASIL_POLICY_BLOCKED_SECRET|CASIL_POLICY_OVERSIZE|CASIL_INTERNAL_ERROR",
  "payload": {
    "reason": "<same as error_code>"
  },
  "room": "<room>",
  "channel": "<channel>",
  "sender": "arqonbus"
}
```

Blocked messages MUST NOT be delivered or persisted.
