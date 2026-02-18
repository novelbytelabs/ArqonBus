# ArqonBus Runbook

Canonical operations runbook:

- `docs/ArqonBus/checklist/runbook.md`

This file exists as a stable top-level entrypoint used by quickstart/tutorial links.

## Quick Ops Checks

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/status
curl -s http://localhost:8080/version
curl -s http://localhost:8080/metrics/prometheus
```

## Notes

- Use `docs/ArqonBus/checklist/runbook.md` for deployment procedures, incident response, CASIL operations, and troubleshooting.
- Keep this alias file in sync if the canonical runbook path changes.
