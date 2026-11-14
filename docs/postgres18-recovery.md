# PostgreSQL 18 bounded recovery

## Scope and observed result

Only the lab PostgreSQL configuration and container were changed. No image version
changed; no volumes were deleted. The old named volume
`ddslab_ddslab_postgres` and the old anonymous parent volume were preserved.
Read-only tar inspection of the failed container's PostgreSQL directory found
only empty directories (`18`, `18/docker`, `data`), not a database cluster.
The previous statement that the old volume had been initialized was incorrect.

Docker Hub documentation retrieval returned HTTP 403. The official entrypoint
inside the pinned PostgreSQL image was inspected instead: its PostgreSQL 18
layout diagnostic requires the parent mount at `/var/lib/postgresql` and links
to docker-library/postgres PR 1259 and issue 37.

## Applied configuration

- Effective PGDATA: `/var/lib/postgresql/18/docker` (confirmed by SQL).
- Volume: `ddslab_ddslab_postgres_v18_recovery`.
- Destination: `/var/lib/postgresql`.
- Image: unchanged pinned PostgreSQL 18.6 Alpine reference in compose.lab.yaml.

Executed twice, scoped strictly to PostgreSQL (the second invocation included
`--force-recreate` to verify persistence):

    docker compose -p ddslab -f compose.lab.yaml up -d --no-deps --pull never postgres

Both recreation commands returned zero. `pg_isready` returned zero after each.
SQL `SELECT system_identifier FROM pg_control_system()` returned the same cluster
identifier before and after recreation. This proves persistence of the initialized
cluster, not application finding persistence: no application tables exist yet.
No volumes were deleted during either recreation.

## Remaining blocker

Initializer, uWSGI, worker and beat had already exited with code 1 during the
original failed startup. They were not restarted or recreated by this recovery.
Nginx and Valkey remain running. Migrations and authenticated API checks remain
BLOCKED, not PASS. Broader application recovery requires reviewing database
credentials and service commands before obtaining approval for any necessary
non-PostgreSQL configuration/recreation changes. Do not reset the new database.

## Validation and evidence

35 pytest tests passed, including a legacy mount rejection test first observed
failing before implementation. Ruff, compileall and git diff --check succeeded.
The preflight now actually renders and inspects Compose when basic validation
passes, and rejects PostgreSQL 18 legacy mounts or incorrect explicit PGDATA.

Runtime evidence (local, not committed):
`evidence/pg18-recovery-1794648819495628368/result.json`.

Commands for offline validation:

    .venv/bin/pytest tests -q
    .venv/bin/ruff check lab tests scripts
    .venv/bin/python -m compileall -q lab tests scripts
    git diff --check

Load ignored local environment and selected pinned images before running the
preflight; never print rendered Compose secrets. No cleanup is authorized.
