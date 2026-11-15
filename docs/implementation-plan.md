# Implementation Plan

## Scope

Build a local-only DefectDojo Security Research Lab with selectable application versions, isolated Compose and Minikube environments, synthetic reports, executable pytest scenarios, state inspection, evidence capture, differential comparison, and bounded performance diagnostics.

## Known host baseline

Collected 2026-11-14T09:37:04+03:30 from the lab directory:

- Ubuntu 26.04.1 LTS, x86_64
- 20 logical CPUs
- 14 GiB RAM, approximately 6.4 GiB available at inventory time, 4 GiB swap
- Root filesystem 228G total, 53G available, 76% used
- Docker Engine 29.9.2 and Compose v5.6.1
- Git 2.53.0, Python 3.14.9, kubectl v1.37.1, Minikube v1.39.0, Helm v3.22.1
- Current Kubernetes context `minikube`; existing profile is stopped and was not changed
- Existing unrelated Docker containers include `admin-panel` and `chat-meilisearch`; existing networks include `ai-security-gate_default`, `librechat_default`, `pipelineguard_default`, and `project-hunter_default`
- Existing upstream checkouts are under `../defect_dojo`; both have local changes and will not be edited by this lab
- No proxy environment variables were present in the captured inventory

See `docs/environment-report.md` for the complete sanitized inventory and command evidence.

## Safety and approval gates

1. Read-only host inspection before every environment action.
2. Do not stop or mutate the existing Minikube profile, unrelated containers, volumes, networks, ports, or repositories.
3. Use a unique Compose project and loopback-only published ports.
4. Use a new, dedicated Minikube profile and namespace only after explicit approval for cluster creation.
5. Do not run destructive reset/prune/remove operations without explicit approval.
6. Do not publish code or contact upstream.
7. Store credentials only in ignored local files; never print or capture secrets.

## Prerequisites and resource policy

The current host is suitable for sequential experiments but not simultaneous Compose and Minikube workloads. Start with one environment at a time. Reserve approximately 6 GiB RAM for Compose and at most 6 GiB for a disposable Minikube profile, scaling down only after readiness checks. Stop the active lab environment before starting the other. Keep at least 20 GiB free disk; stop before large image pulls if that threshold is crossed.

Required tools: Python 3, Git, Docker Engine with Compose v2. Kubernetes phase additionally requires kubectl, Minikube, and Helm. Optional tools must be detected and the affected phase reported BLOCKED rather than guessed.

## Phase 0 — inventory

- Create `docs/environment-report.md` from read-only commands.
- Record OS, CPU, RAM, disk, Docker, Compose, Python, Git, Kubernetes context, Minikube, Helm, network/proxy configuration, listeners, existing containers/networks/volumes, and upstream checkout status.
- Detect port conflicts before binding any lab service.
- Re-run inventory after each environment lifecycle change.

## Phase 1 — repository and version control

- Add repository layout, `.gitignore`, `.env.example`, Python metadata, pinned direct dependencies, Makefile, and safe scripts.
- Add `configs/versions.yaml` for 3.5.101, 3.4.304, and an explicitly supplied development SHA. Keep source ref, image digest, and Helm chart version separate.
- Verify availability of each selected ref/image/chart/documentation independently; record unavailable values as BLOCKED, never substitute.
- Keep `upstream/` ignored and provide clone/worktree commands that never touch the sibling checkout.
- Add unit tests for version metadata parsing and canonical result normalization.

## Offline milestone completed

The typed configuration, result model, evidence writer, and deterministic synthetic fixture generator are implemented and tested in the lab package. The offline checks are:

```text
uv run --project . pytest tests -q
uv run --project . ruff check lab tests scripts
python3 -m py_compile lab/*.py tests/unit/*.py
git diff --check
```

The next milestone is Compose preflight/config rendering only; no services are started by this change.

## Phase 2 — Compose baseline

- Read the pinned upstream `docker-compose.yml` and contributor/parser guidance before creating a lab-owned Compose overlay with a unique project name, loopback-only UI binding, isolated named volumes, and explicit selected image/source settings.
- Implement lifecycle scripts with preflight checks, readiness polling, migration check, and API smoke test.
- Bootstrap only synthetic Product, Engagement, Test, and local credentials through documented APIs.
- Save sanitized request/response evidence and never print tokens.
- Provide non-destructive stop and an explicitly gated reset for lab-owned volumes only.
- Acceptance gate: actual API smoke test plus at least one real parser smoke test and one real import/reimport test, each with evidence.

## Phase 3 — pytest harness

- Add typed configuration, httpx client, authentication fixture, object factories, report import helpers, semantic normalization, and result statuses PASS/FAIL/SKIP/BLOCKED/INCONCLUSIVE.
- Capture request metadata and sanitized responses.
- Use stable logical identities rather than database IDs, timestamps, ordering, or generated hashes.
- Add executable scenario manifests and evidence directory creation.

## Phase 4 — parser robustness

- Read current parser conventions and supported parser names from the selected release.
- Generate licensed/synthetic Nmap, SARIF, Trivy, Trivy Operator, Generic Findings Import, Govulncheck, and one supported dependency-scanner fixtures.
- Cover 0/1/many findings, missing/null/empty optional fields, ordering changes, identifiers, severity/location mapping, invalid encoding, and bounded truncation cases.
- Treat unsupported parser/setup errors as SKIP or BLOCKED, not bugs. Bound file size and execution time.

## Phase 5 — import/reimport integrity

- For each supported parser, run initial import, identical reimport, removal, addition, line/path change, resource identity change, `close_old_findings` true/false, dedup/reactivation, and applicable suppression/risk-acceptance cases.
- Record the matching algorithm and configuration.
- Assert invariants around multiplication, closure, presence, status preservation, resource identity, audit history, and metadata.
- Store normalized outcomes for differential comparison.

## Phase 6 — API security

- Create synthetic authorized and unauthorized users only inside the lab.
- Test authentication, product/engagement object boundaries, invalid identifiers, bounded oversized inputs, malformed reports, safe errors, report access, and status transitions.
- Do not run unbounded fuzzing or destructive actions.

## Phase 7 — Minikube and Helm

- Require explicit approval before creating a new profile.
- Read current pinned chart values and upgrade notes before rendering overrides.
- Deploy into a new profile and namespace with loopback-only access and synthetic credentials.
- Add an in-cluster mail receiver and test SMTP, worker, password-reset, notification, secret propagation, rollout failure, upgrade, and disposable-install rollback behavior.
- Prove running resources and preserved state before claiming completion.

## Phase 8 — differential testing

- Run identical supported scenarios against 3.4.304, 3.5.101, and the pinned development SHA, each with isolated state.
- Record input hash, image digest, source SHA, chart version, settings, and timestamps.
- Compare semantic invariants, then classify differences as expected release change, possible regression, setup difference, or unknown/inconclusive.
- Read release/upgrade notes and search upstream issue/PR history before any regression claim. Do not submit externally.

## Phase 9 — performance

- Generate deterministic 100-finding first, then 1000 and 3000 only when safe.
- Measure elapsed time, status, row deltas, query counts where available, CPU, RSS, and transaction behavior under limited concurrency/resource caps.
- Compare repeated equivalent runs and clearly label results synthetic/non-production.

## Phase 10 — evidence and triage

Each experiment directory must contain `scenario.yaml`, `metadata.json`, `summary.md`, sanitized request/response files, relevant logs, environment/version metadata, reproduction commands, and fixture checksums. Candidate bug workflow: clean baseline reproduction, independent reproduction, minimal input, previous/development comparison, release-note review, duplicate search, conservative severity, and report draft. Security-sensitive details remain private and require explicit approval before any upstream action.

## Rollback and cleanup

Normal stop removes only lab processes, not data. Destructive reset is limited to explicitly named lab-owned Compose volumes or a disposable Minikube profile and must require approval. Never use global Docker Engine prune, volume prune, cluster delete, or broad kill commands. If a port conflict appears, stop and choose a different loopback port rather than changing the conflicting service.

## First implementation order

1. Finish Phase 0 evidence and repository metadata.
2. Add unit-testable configuration, result model, evidence writer, and synthetic fixture generator.
3. Add Compose preflight/config rendering without starting services.
4. After review/approval, start the isolated Compose project and run API smoke/import/reimport gates.
5. Only after those gates pass, expand parser, API, differential, performance, and Kubernetes phases.
