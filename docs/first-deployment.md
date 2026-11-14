# First controlled Compose deployment

This runbook is for Milestone 2C. It is not executed by the artifact-readiness milestone. Starting services requires explicit human approval after the preflight is reviewed.

## Prerequisites

- Ubuntu host with Docker Engine and Compose v2.
- Host architecture compatible with the selected image platform. The current host is `linux/amd64`; Debian AMD64 is the officially supported Open Source configuration.
- At least 6 GiB available RAM for a sequential Compose run and at least 20 GiB free disk.
- No simultaneous Minikube workload.
- A free loopback port selected after a fresh listener check.
- Exact verified application image references and digests in `configs/artifacts.yaml`.
- No active use of the dedicated project name `ddslab`.

## Generate local secrets

Run from this repository, never from an upstream checkout:

```text
python3 scripts/generate_secrets.py --output .env.lab
chmod 600 .env.lab
```

The generator uses the OS cryptographic random source, refuses to overwrite an existing file, prints no secret values, and writes mode 0600. `.env.lab` is ignored by Git.

## Configure selected artifacts

For baseline 3.5.101, set these values in the shell or an ignored environment file:

```text
DD_NGINX_IMAGE=defectdojo/defectdojo-nginx:3.5.101@sha256:966e218d2f12d89305fc90d398ec00c2bcbd0fe5de1aca0a39b5824aabe937c7
DD_DJANGO_IMAGE=defectdojo/defectdojo-django:3.5.101@sha256:b396838e51706862aca6389589ffc237245d36d80fffb385218f4d8fedc98fad
```

Use the corresponding previous-version references only when the scenario explicitly selects 3.4.304. Never use `latest`, a moving branch, or an unverified digest.

## Preflight

```text
set -a
. ./.env.lab
set +a
python3 -m lab.preflight --version baseline --output evidence/preflight-baseline.json
```

PASS criteria:
- Artifact metadata is verified.
- All required variables exist.
- UI binding is `127.0.0.1`.
- The selected port is unused and loopback-only.
- No public PostgreSQL or Valkey port exists.
- No unexpected bind mount exists.
- Host resource checks meet the lab policy.
- The rendered Compose model contains only the seven documented services and three lab-owned volumes.

BLOCKED criteria:
- Missing/unknown image digest or architecture.
- Missing development SHA.
- Missing or unsafe credential.
- Port conflict, public binding, unexpected mount, or project-name conflict.
- Insufficient resources.

## Render without starting

```text
docker compose -p ddslab -f compose.lab.yaml config
```

Review the output locally without copying secrets into evidence. The command must return zero and must not be replaced with `up`, `pull`, or any lifecycle operation.

## Controlled startup after approval

```text
docker compose -p ddslab -f compose.lab.yaml up -d
```

This command is intentionally not run by Milestone 2B.

## Health and initialization validation

After approval and startup, validate only the dedicated project:

```text
docker compose -p ddslab -f compose.lab.yaml ps
docker compose -p ddslab -f compose.lab.yaml logs --no-color initializer
docker compose -p ddslab -f compose.lab.yaml exec -T uwsgi python manage.py check
curl --fail http://127.0.0.1:18080/api/v2/
```

PASS requires running/readiness state, successful initialization, Django checks, and an authenticated API smoke test with a locally generated token. Do not interpret container existence alone as application health.

## Evidence capture

Create a unique evidence run directory with the lab evidence writer. Record sanitized status, selected version, source SHA, image digests, command exit codes, fixture checksums, and health summaries. Do not save `.env.lab`, tokens, passwords, rendered secret values, or raw secret-bearing logs.

## Failure recovery

Stop and classify the failure before changing anything. Preserve logs under sanitized evidence. Do not reset volumes or change unrelated resources. A malformed configuration is a setup failure; an unavailable artifact is BLOCKED; only a reproducible application assertion failure is a candidate product issue.

## Safe shutdown and cleanup

After approval:

```text
docker compose -p ddslab -f compose.lab.yaml stop
```

Project-scoped volume deletion is intentionally not included. Any deletion of `ddslab_*` volumes requires separate explicit approval after confirming ownership. Never run global prune commands.
