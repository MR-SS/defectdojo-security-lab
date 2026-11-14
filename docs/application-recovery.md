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
Both are required by Compose. First-boot credentials have now been appended to
ignored .env.lab using cryptographic randomness and an atomic mode-0600 update.
Existing values, including the database credential, were preserved. The inspected
initialization code prints these secrets only when their explicit values are absent.

## Required gates before execution

Confirm database authenticated SELECT succeeds and Valkey returns PONG before
initializer creation. These external readiness checks are mandatory because
service_started is not readiness. Execute `.venv/bin/python -m lab.startup`
immediately before the first lifecycle command; abort on any nonzero exit.
It renders configuration privately, checks credentials against the database
container, executes authenticated TCP read-only SQL and requires Valkey PONG.
Each subprocess is bounded to 15 seconds; PostgreSQL connection and statement
timeouts are 5 seconds. TCP uses service DNS, but originates in the existing
infrastructure containers rather than an application container. This limitation
must be closed by application readiness checks after approved recreation.

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
services. Rendered config was inspected only in memory. The live host-side gate
passed with persistent local first-boot credentials. No lifecycle command ran.

Provisioning command (idempotent, never rotates existing values):

    .venv/bin/python -m scripts.generate_secrets --first-boot --output .env.lab

Before approved lifecycle commands, load .env.lab into a private process
environment and load DD_DJANGO_IMAGE / DD_NGINX_IMAGE from the baseline record in
configs/versions.yaml. Never enable shell tracing or print the resulting config.
Run the readiness gate again immediately before initializer recreation.
Bound each compose up command to 90 seconds; initializer wait to 600 seconds;
application and each Celery readiness stage to 120 seconds. Stop progression on
timeout or failure without terminating containers. After initialization, require
`manage.py migrate --check` success and nonempty migration records; require the
product, engagement, test and finding tables. Require worker control ping and
beat scheduling evidence. Finally verify missing authentication is rejected and
an authenticated API GET succeeds without persisting tokens or credentials.
