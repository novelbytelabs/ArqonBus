# Continuum Projector Postgres Migration + Backup/Restore Runbook

Last updated: 2026-02-20

## Scope

Operational procedure for Continuum projector tables:

- `arqonbus_continuum_projection`
- `arqonbus_continuum_projection_events`
- `arqonbus_continuum_projection_dlq`

## Prerequisites

- `psql`, `pg_dump`, and `pg_restore` available on operator host.
- `ARQONBUS_POSTGRES_URL` set to target Postgres instance.
- Maintenance window approved for production apply.

## Migration Apply

```bash
psql "$ARQONBUS_POSTGRES_URL" -v ON_ERROR_STOP=1 \
  -f scripts/migrations/20260220_continuum_projector_postgres.sql
```

Post-check:

```bash
psql "$ARQONBUS_POSTGRES_URL" -v ON_ERROR_STOP=1 -c \
"SELECT to_regclass('public.arqonbus_continuum_projection') AS projection,
        to_regclass('public.arqonbus_continuum_projection_events') AS events,
        to_regclass('public.arqonbus_continuum_projection_dlq') AS dlq;"
```

## Logical Backup

```bash
mkdir -p backups
pg_dump "$ARQONBUS_POSTGRES_URL" \
  --format=custom \
  --no-owner \
  --table=public.arqonbus_continuum_projection \
  --table=public.arqonbus_continuum_projection_events \
  --table=public.arqonbus_continuum_projection_dlq \
  --file="backups/arqonbus_continuum_projector_$(date -u +%Y%m%dT%H%M%SZ).dump"
```

## Restore (Table-Scoped)

Restore into a clean target DB or a maintenance window after truncation:

```bash
pg_restore "$ARQONBUS_POSTGRES_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --table=public.arqonbus_continuum_projection \
  --table=public.arqonbus_continuum_projection_events \
  --table=public.arqonbus_continuum_projection_dlq \
  backups/<backup-file>.dump
```

## Integrity Verification

```bash
psql "$ARQONBUS_POSTGRES_URL" -v ON_ERROR_STOP=1 -c \
"SELECT
    (SELECT COUNT(*) FROM arqonbus_continuum_projection) AS projection_rows,
    (SELECT COUNT(*) FROM arqonbus_continuum_projection_events) AS event_rows,
    (SELECT COUNT(*) FROM arqonbus_continuum_projection_dlq) AS dlq_rows;"
```

Run application-level verification:

```bash
conda run -n helios-gpu-118 python -m pytest -q \
  tests/integration/test_continuum_projector_postgres.py \
  tests/integration/test_continuum_projector_postgres_e2e.py
```

## Rollback Guidance

- If migration apply fails before commit, rerun after fix; no partial state persists.
- If restore causes mismatch, repeat restore from known-good backup.
- Stop ArqonBus write traffic before repeated restore attempts.
