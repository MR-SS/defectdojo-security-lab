# DefectDojo Security Research Lab

A local-only, reproducible lab for testing DefectDojo Open Source releases, parser behavior, import/reimport integrity, API authorization, deployment compatibility, differential behavior, and bounded performance.

This repository contains lab code and synthetic fixtures only. Upstream DefectDojo checkouts remain outside this repository and are never modified by lab bootstrap.

## Current status

Target release: **DefectDojo 3.5.101** (pinned source SHA and image digests in `configs/versions.yaml`). The lab has completed investigations across SARIF identity, Trivy Operator ReplicaSet identity, and XML import reliability:

- **SARIF #14205** — closed with an evidence-bounded assessment; no upstream report justified.
- **Trivy #16026 (5A/5B)** — parser-level identity churn reproduced with synthetic fixtures; normalization contract documented; no patch without maintainer clarification.
- **XML #14752 (6A)** — malformed XML raises unhandled `ParseError` reaching a generic HTTP 500 (reliability gap; upstream issue remains open). No XXE/SSRF/DoS demonstrated.
- **XML empty-report lifecycle (6B–6F)** — `XML-EMPTY-CONTROL` executed once under explicit approval: a parser-accepted `<testsuites/>` empty report legitimately closed the three baseline findings under `close_old_findings=true` (PASS as lifecycle control, not a defect). `XML-INVALID-ROOT` harness is prepared and approval-gated; not executed.

Nothing observed so far is classified as a security vulnerability.

## Safety

- Local-only bindings are required.
- Never commit `.env`, tokens, passwords, logs containing secrets, volumes, or customer data.
- Use a dedicated Compose project and a dedicated Minikube profile/namespace.
- Destructive operations, host-wide changes, upgrades, and actions against existing environments require explicit human approval.
- No upstream issue, pull request, commit push, or maintainer contact is performed by this repository's tooling.

### Scenario approval gates

Every mutating scenario requires all of:

- `DDSLAB_RUN_INTEGRATION=1` (global opt-in)
- `DDSLAB_APPROVE_SCENARIO=<exact scenario name>` (per-scenario, single-use; one scenario's approval can never authorize another)
- `DDSLAB_SOURCE_CHECKOUT` pointing at a verified clean worktree of the pinned commit
- Fixture SHA-256 verification, runtime/source hash correspondence, Product Type 3 isolation, synchronous completion, and exact before/after Finding readbacks

Failures raise `GateBlocked` and never retry. Evidence is sanitized before writing; credentials live only in ignored local files.

## Repository layout

- `lab/` — typed models, deterministic fixtures, evidence writer, preflight, startup gates, and the approval-gated XML lifecycle runners (`xml_lifecycle.py`)
- `configs/` — version selections and runtime configuration
- `scripts/` — safe setup, lifecycle, inspection, and evidence commands
- `fixtures/` — synthetic scan reports (Generic Findings, Nmap XML, Trivy Operator JSON, Burp Dastardly XML under `fixtures/xml-6b/`)
- `tests/` — pytest unit and integration tests
- `docs/` — sanitized plans, inventory, matrices, and investigation results
- `evidence/` — ignored experiment outputs

## Prerequisites

Ubuntu, Python 3, Git, Docker with Compose v2, and optionally kubectl/Minikube for the Kubernetes phase. Check `docs/environment-report.md` before starting services.

## Commands

```text
make inventory
make test-unit
make compose-config VERSION=3.5.101
make evidence SCENARIO=<scenario-id>
```

Offline validation:

```text
.venv/bin/python -m pytest -m 'not integration' -q
.venv/bin/ruff check lab tests scripts
.venv/bin/python -m compileall -q lab tests
```

Approval-gated live entrypoints (inert without the exact env vars above):

```text
tests/integration/test_xml_6c.py::test_xml_empty_control_live_entrypoint
tests/integration/test_xml_6c.py::test_xml_invalid_root_live_entrypoint
```

## Version selection

Selections are machine-readable in `configs/versions.yaml`. Values are independently recorded for source tag/SHA, image digest, and Helm chart version. No version is silently substituted.

## Safe Compose preflight

The lab-owned `compose.lab.yaml` and `lab/preflight.py` provide configuration-only validation. They do not start, pull, stop, remove, or reset services.

```text
python3 -m lab.preflight --version baseline --output evidence/preflight-baseline.json
```

The preflight remains BLOCKED while application image digests or required local credentials are missing. See `docs/compose-preflight.md`.

## Scope

Research tooling for local, isolated testing only. Do not point these harnesses at instances you do not own.
