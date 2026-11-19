# DefectDojo Security Research Lab

> **Portfolio summary:** Independent security engineering research into parser contracts, vulnerability import/reimport integrity, reproducible fixtures and controlled validation. The findings below are specific to documented test conditions. [Related upstream pull requests: #16888](https://github.com/DefectDojo/django-DefectDojo/pull/16888) and [#16889](https://github.com/DefectDojo/django-DefectDojo/pull/16889) are submitted work, not claims of acceptance or merge. Verify their live status on GitHub before describing them otherwise.


An independent, local-first research project for studying DefectDojo Open Source
behavior under controlled conditions. The lab focuses on scan-parser contracts,
import and reimport lifecycle safety, identity stability, and reproducible
evidence collection. It is not affiliated with, endorsed by, or operated by
the DefectDojo project.

The repository contains synthetic fixtures, deterministic test harnesses, and
sanitized technical records. Upstream source checkouts, local credentials,
runtime logs, and experiment evidence remain outside version control.

## Research objectives

- Characterize parser behavior with small, synthetic reports.
- Test import and reimport invariants in isolated, approval-gated environments.
- Distinguish observed defects from parser-level observations and hypotheses.
- Preserve enough configuration, fixtures, and checksums for an independent
  researcher to repeat the offline work.
- Prepare narrowly scoped upstream contributions when the evidence supports one.

## Confirmed findings and investigation outcomes

The findings below are bounded to the pinned releases and test conditions
documented in the linked reports. They are not CVE claims or general statements
about every DefectDojo deployment.

- **Burp Dastardly invalid-root integrity defect — confirmed.** A well-formed
  XML document with an unsupported root could be interpreted as an empty
  Dastardly result. In an isolated, approved reimport scenario with
  `close_old_findings=true`, that result mitigated existing findings. A minimal
  root-validation patch and regression tests are prepared locally, but have not
  been submitted upstream. See the [XML lifecycle preparation record](docs/xml-6c-regression.md)
  and [empty-report integrity analysis](docs/xml-6b-empty-integrity.md).
- **Malformed and structurally invalid XML — parser/importer reliability
  observations.** The bounded Dastardly investigation found several invalid
  inputs that reach generic error handling at the tested seam. It did not
  establish an access-control bypass, XXE, SSRF, denial of service, or a new
  security vulnerability. See the [XML investigation](docs/xml-14752-investigation.md).
- **SARIF identity investigation — no new upstream report recommended.**
  Synthetic controls did not reproduce the reported mass-closure outcome on the
  pinned release. See the [final assessment](docs/sarif-14205-final-assessment.md).
- **Trivy Operator ReplicaSet identity — unresolved parser-level hypothesis.**
  Source and synthetic analysis indicate that rollout-generated names can affect
  identity inputs; a maintainer-aligned reproduction is still needed before an
  upstream fix is proposed. See the [triage](docs/trivy-16026-triage.md) and
  [normalization contract](docs/trivy-16026-normalization-contract.md).

## Research methodology

The lab uses a deliberately narrow workflow:

1. Pin the application source, image references, and fixture bytes.
2. Establish a parser-only control with synthetic data.
3. Treat live lifecycle experiments as separate, explicitly approved work.
4. Record complete before/after state and fail closed when provenance or safety
   gates do not hold.
5. Report only what the evidence establishes, including negative and
   inconclusive outcomes.

The [version matrix](docs/version-matrix.md), [Compose preflight](docs/compose-preflight.md),
and [lifecycle semantics note](docs/close-old-findings-semantics.md) describe
the reproducibility and safety constraints in detail.

## Repository architecture

| Path | Purpose |
| --- | --- |
| `lab/` | Research models, safety gates, fixture helpers, lifecycle oracles, and parser analyses. |
| `fixtures/` | Small synthetic reports used by offline tests and controlled experiments. |
| `tests/` | Unit tests, parser probes, and explicitly gated integration entrypoints. |
| `configs/` | Version selections and immutable artifact metadata. |
| `docs/` | Detailed investigation records, methodology, and environment notes. |
| `upstream-proposals/` | Local-only upstream contribution material; not an upstream checkout. |
| `evidence/` | Reserved for ignored local experiment output; only `.gitkeep` is tracked. |

## Quick start

The default workflow is offline. It does not start containers or contact a
DefectDojo instance.

```bash
git clone https://github.com/MR-SS/defectdojo-security-lab.git
cd defectdojo-security-lab
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[quality]'
make test-unit
.venv/bin/ruff check lab tests scripts
```

Inspect the pinned research configuration without starting services:

```bash
make inventory
make compose-config VERSION=3.5.101
```

`compose-up` and `smoke` intentionally do not start a lab. Any future live
experiment requires a dedicated local environment and the explicit approval
gates described below.

## Reproducibility and experiment controls

`configs/versions.yaml` records the selected release, source SHA, image
digests, and chart metadata. Fixtures are synthetic and are validated by the
test suite. Live-capable scenarios require all of the following:

- `DDSLAB_RUN_INTEGRATION=1`;
- `DDSLAB_APPROVE_SCENARIO` set to the exact scenario name;
- a clean, verified upstream source checkout selected through
  `DDSLAB_SOURCE_CHECKOUT`;
- fixture-hash and source/runtime correspondence checks; and
- complete, scoped before/after readbacks.

These controls are designed to prevent an approval for one scenario from
authorizing another. Local credentials belong in ignored files such as
`.env.lab`; generated output belongs under `evidence/` and is not committed.

## Upstream contributions

The Burp Dastardly root-validation patch is maintained separately as a local
prepared contribution with focused tests and fixtures. It has **not** been
pushed or submitted as a pull request. The public lab retains the relevant
evidence and lifecycle analysis without publishing the separate contribution
artifact.

Other investigations remain either evidence-bounded conclusions or unresolved
hypotheses. This repository does not create issues, pull requests, or other
external communications automatically.

## Safety and responsible research

- Use only systems and accounts you own or are explicitly authorized to test.
- Keep bindings local and use a dedicated Compose project, namespace, and
  storage for experiments.
- Never commit credentials, customer reports, private source snippets, runtime
  volumes, or local evidence.
- Do not run live imports, reimports, cleanup, or destructive operations without
  separately reviewing and approving the exact scenario.
- Treat parser behavior and test-seam results as scoped evidence, not as proof
  of broad exploitability.

## Project status

The offline research harness and reproducibility controls are active. Confirmed
results, parser observations, and unresolved hypotheses are maintained in
`docs/`; detailed records remain available without making the README an
execution diary. The current upstream contribution is prepared locally and is
awaiting an explicit publication decision.
