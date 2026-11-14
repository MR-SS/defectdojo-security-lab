# Application recovery proposal (approval required)

No containers were started or recreated while preparing this change.

## Changes

Only initializer, uwsgi, celeryworker and celerybeat service definitions change.
Database URLs now interpolate the existing database user and password rather than
using the old passwordless URL. The existing generated password was verified to
match the running database container and to parse unchanged in the rendered URL.
No password was rotated. Arbitrary future passwords containing URL delimiters
will require percent encoding; do not substitute such credentials silently.

Entrypoints match the exact baseline source Compose scripts and were verified
executable in the pinned application container. Runtime services require
initializer service_completed_successfully. PostgreSQL/Valkey use service_started
semantics, matching upstream; this is NOT a readiness guarantee. No healthchecks
were added to these unchanged infrastructure services.

## First-boot logging blocker

The pinned complete_initialization command prints generated administrator and
JIRA webhook secrets when DD_ADMIN_PASSWORD or DD_JIRA_WEBHOOK_SECRET are absent.
Both are now required by Compose. Validation used ephemeral in-memory values for
these two variables, never logged or saved; they are NOT deployment credentials.
Persistent local first-boot credentials still need provisioning in ignored local
configuration before approval to execute. Existing .env.lab was not modified.

## Required gates before execution

Confirm database authenticated SELECT succeeds and Valkey returns PONG before
initializer creation. These external readiness checks are mandatory because
service_started is not readiness. The automatic initializer readiness contract
is not yet implemented; do not treat config rendering as passing that gate.

Load existing local configuration and verified image references without printing
values. Provision first-boot secrets without logging them. Then, only after
explicit approval, execute each stage separately:

    docker compose -p ddslab -f compose.lab.yaml up -d --no-deps --pull never initializer
    timeout 600 docker wait ddslab-initializer-1

Require initializer State.ExitCode=0. Timeout means stop further activity and
request instructions, not permission to stop containers. Verify migration records
and required auth/product/engagement/test/finding tables. Initialization may load
the release schema snapshot, apply migrations, install audit triggers, create an
administrator and seed reference data. It is a database write, not a smoke read.

    docker compose -p ddslab -f compose.lab.yaml up -d --no-deps --pull never uwsgi

Within 120 seconds require Django checks and local HTTP readiness, with no public
host binding. Stop on failure; do not start workers until this passes.

    docker compose -p ddslab -f compose.lab.yaml up -d --no-deps --pull never celeryworker
    docker compose -p ddslab -f compose.lab.yaml up -d --no-deps --pull never celerybeat

Verify Celery control ping and beat scheduler startup, not merely container state.
Then perform an authenticated, sanitized API smoke test using a synthetic account.
No runtime tests have been executed for this proposal.

## Preservation / rollback

PostgreSQL, Valkey, nginx and volume definitions are unchanged. Only the four
application containers require replacement. Do not apply the whole stack or pull
images. No schema downgrade, volume deletion, reset or automatic rollback is
approved. On failure retain state and sanitized evidence and request instructions.

## Validation scope

Exact source HEAD matched configs/versions.yaml baseline SHA. All four configured
entrypoint scripts matched upstream and had executable mode in the pinned image.
Rendered database credentials matched the current database container for all four
services. Rendered config was inspected only in memory. First-boot credentials
used for rendering were ephemeral. Remaining readiness/provisioning gates mean
this proposal is not yet an executable deployment approval request.
