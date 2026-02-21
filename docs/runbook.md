# ArqonBus Runbook

Canonical operations runbook:

- `docs/ArqonBus/checklist/runbook.md`

This file exists as a stable top-level entrypoint used by quickstart/tutorial links.

## Quick Ops Checks

```bash
export ARQONBUS_HTTP_URL="${ARQONBUS_HTTP_URL:-http://127.0.0.1:8080}"
curl -s "${ARQONBUS_HTTP_URL}/health"
curl -s "${ARQONBUS_HTTP_URL}/status"
curl -s "${ARQONBUS_HTTP_URL}/version"
curl -s "${ARQONBUS_HTTP_URL}/metrics/prometheus"
```

## Notes

- Use `docs/ArqonBus/checklist/runbook.md` for deployment procedures, incident response, CASIL operations, and troubleshooting.
- Environment profile contract (`dev|staging|prod`) and strict preflight requirements are defined in `docs/ArqonBus/checklist/runbook.md`.
- Keep this alias file in sync if the canonical runbook path changes.
