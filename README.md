# DefectDojo Security Research Lab

A local-only, reproducible lab for testing DefectDojo Open Source releases, parser behavior, import/reimport integrity, API authorization, deployment compatibility, differential behavior, and bounded performance.

This repository contains lab code and synthetic fixtures only. Upstream DefectDojo checkouts remain outside this repository and are never modified by lab bootstrap.

## Current status

Phase 0 host inventory and Phase 1 repository bootstrap are in progress. See `docs/environment-report.md`, `docs/implementation-plan.md`, and `docs/version-matrix.md`.

The existing host has an active Minikube profile in `Stopped` state and unrelated Docker containers/networks. The lab does not start, stop, reset, prune, or remove those resources automatically.

## Safety

- Local-only bindings are required.
- Never commit `.env`, tokens, passwords, logs containing secrets, volumes, or customer data.
- Use a dedicated Compose project and a dedicated Minikube profile/namespace.
- Destructive operations, host-wide changes, upgrades, and actions against existing environments require explicit human approval.
- No upstream issue, pull request, commit push, or maintainer contact is performed by this repository.

## Repository layout

- `configs/`: version selections and runtime configuration
- `scripts/`: safe setup, lifecycle, inspection, and evidence commands
- `scenarios/`: named executable scenario definitions
- `fixtures/`: synthetic scan reports
- `tests/`: pytest unit and integration tests
- `benchmarks/`: bounded performance harnesses
- `observability/`: local diagnostics and metrics helpers
- `evidence/`: ignored experiment outputs
- `docs/`: plans, inventory, matrix, operations, and triage guidance
- `upstream/`: ignored local clones/worktrees only

## Prerequisites

Ubuntu, Python 3, Git, Docker Engine with Compose v2, and optionally kubectl, Minikube, and Helm for the Kubernetes phase. Check `docs/environment-report.md` before starting services.

## Planned commands

The lifecycle commands will be added incrementally and must refuse unsafe defaults:

```text
make inventory
make test-unit
make compose-config VERSION=3.5.101
make compose-up VERSION=3.5.101
make smoke VERSION=3.5.101
make compose-down VERSION=3.5.101
make evidence SCENARIO=<scenario-id>
```

Until a command exists, it is intentionally not advertised as executable.

## Version selection

Selections are machine-readable in `configs/versions.yaml`. Values are independently recorded for source tag/SHA, image digest, and Helm chart version. No version is silently substituted.
