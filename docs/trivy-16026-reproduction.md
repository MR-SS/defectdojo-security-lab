# Milestone 5A: ReplicaSet identity, parser-only baseline

Baseline lab commit: 0750281ddeced1a58a27471cb05550656c21a86f.
DefectDojo 3.5.101 source: 32aea6841a019b050737c8874b939b236095333e. Runtime parser.py and all three
handler files were compared byte-for-byte with pinned git objects successfully.
No application files were changed. No findings were saved, no imports/reimports
were called, and no infrastructure was changed. The probe uses unsaved Test,
Test_Type and Finding instances; its SQL wrapper refuses non-SELECT statements.

## Reproduction

Run `PYTHONPATH=. .venv/bin/python tests/trivy_parser_probe.py` from the lab root.
This uses the existing ddslab-uwsgi-1 container, not a newly deployed environment.
The six fixtures are minimal parser inputs, not full Kubernetes CRD validation
fixtures. Each report list contains alpha and an unrelated beta workload.
Only alpha's resource-name label changes between reports:
`alpha-6b7c8d9f5b` -> `alpha-7c8d9f6b5c`. These are synthetic hash-shaped suffixes,
not measured hashes of actual PodTemplates. Metadata omitted by this minimal
representation is not evidence about a deployed cluster or ownership.

Namespace synthetic, kind ReplicaSet, container app, image, package, version,
vulnerability/check/secret entry and all other report fields remain identical.
The secret match is NOT_A_CREDENTIAL. No embedded links are followed.

Complete descriptions, services, fields and calculated hashes are captured in
`trivy-16026-parser-results.json`. Each of vulnerabilities, checks and secrets
independently produces two findings before and two after. Alpha changes service,
description and calculated hash; beta remains byte-for-byte identical in the
captured output and distinct from alpha. All findings remain unsaved.

The service changes from `synthetic/ReplicaSet/alpha-6b7c8d9f5b/app`
to `synthetic/ReplicaSet/alpha-7c8d9f6b5c/app`.
The only description change is the value on the `**resource.name:**` line.
Effective algorithm is hash_code; fields are title, severity, vulnerability_ids,
description, with service always included. With service overwritten in memory
by `synthetic-stable-request`, each handler still changes hash. This isolates
remaining description volatility; it is NOT an importer execution.

Conclusion: parser-level identity churn is reproduced for all three handlers.
Incorrect closure, persisted matching and lifecycle outcomes are not reproduced.

## Source-backed naming contract (proposal, not implemented)

Kubernetes v1.35.0 sources inspected through the GitHub contents API:
- pkg/controller/controller_utils.go:1395-1406, ComputeHash: FNV32a of the
  PodTemplate plus optional collision count, decimal uint32 passed to SafeEncodeString.
- pkg/controller/deployment/sync.go:198-210 and generateReplicaSetName:
  deployment name + hyphen + encoded hash, truncating a long deployment name.
- kubernetes/apimachinery v0.35.0 pkg/util/rand/rand.go:121-126:
  character-wise encoding, not hexadecimal and not arbitrary random text.

Consequently a fixed ten-character regex alone is not the exact contract:
encoded decimal uint32 has variable length. A recognizer can decode the suffix,
require canonical decimal representation in uint32 range and re-encode it.
That verifies syntax, not Deployment ownership. A custom ReplicaSet can have
exactly the same spelling. No name-only helper can guarantee both automatic
normalization and preservation of all intentionally custom names.

Trivy Operator pkg/kube/object.go inspected at blob aa8050a628ea2c3d0e25297bd1220c460ef9f0ec:
ObjectRefToLabels and ObjectToObjectMeta preserve resource kind/name/namespace;
long names use a name-hash label and, in ObjectToObjectMeta, an annotation with
the original name. ReportOwner resolves Deployment to ReplicaSet and leaves
ReplicaSet ownership at that level. The report's ReplicaSet owner reference is
not proof of that ReplicaSet's Deployment parent. This was current source,
not a claim about every historical Trivy Operator release.

Proposed helper contract:
1. Accept kind, original name and explicit verified Deployment provenance.
2. Return original unchanged for non-ReplicaSet, missing/malformed names,
   unsupported metadata, custom/unowned ReplicaSets or uncertain provenance.
3. Require exact reconstructed controller-generated name and valid encoded
   suffix; retain the entire logical Deployment name (including internal hyphens).
4. Preserve namespace, resource kind and container outside the helper.
5. Use the same resolved logical name in service and description. Retain raw
   generation metadata outside identity-bearing fields where possible.
6. Fail unchanged for truncated names without the full owner identity; never
   normalize a resource-name-hash label as if it were the original name.

If ordinary reports cannot supply parent provenance, an explicit opt-in,
producer-supported metadata contract is needed. A regex-only fallback would
need maintainer approval of its custom-name collision risk; it does not meet
an unconditional confidently-identified guarantee.

Required future tests: verified two-generation Deployment pair; distinct alpha
and beta; hyphenated Deployment names; stable custom names; custom names with
valid-looking hashes; missing/contradictory provenance; malformed/unsupported
metadata; decimal encoding boundaries; long/truncated names; missing name label
with annotation/hash fallback; non-ReplicaSet kinds unchanged; service and
description normalization together. No normalization implementation or claimed
normalization test success is included in this milestone.

## Future lifecycle experiments (separate approvals)

Run each handler and each service variant in a fresh isolated Product/Engagement,
with one Test, exactly one import and one same-Test reimport. Include beta in
both reports. Require unchanged hash_code configuration, synchronous completion,
global deduplication disabled, initial close_old_findings=false, reimport
close_old_findings=true, product-wide closure=false, no retries or cleanup.
Capture exact IDs, hashes, services, descriptions, ownership, duplicate and
active/mitigated states, and complete pagination. Stop on failed preflight.

A: request service omitted in both operations. Predicted unpatched baseline:
initial two active findings; changed alpha does not hash-match, creating one
new record; beta matches its original. Original alpha has nonempty parser
service and is outside the null/empty request-service closure scope. Predicted
final three active records, no closure. This is not a measured outcome.

B: explicit identical stable request service for both operations. Both initial
findings receive that service. Description still changes alpha's hash. Predicted
one new alpha, beta matched, original alpha closed: three records, two active
and one mitigated. Beta must remain separate despite shared request service.
These predictions assume no unrelated findings and no other deduplication or
lifecycle overrides. Actual API execution remains approval-gated.

Source: default_reimporter.py:326-328 selects closure originals by request service;
:1038-1041 matches hash candidates; :1262-1341 handles matched active findings.
See also default_importer.py service override and docs/trivy-16026-triage.md.
Do not conflate Import sibling-Test closure with same-Test Reimport closure.
A successfully justified future normalization should yield two retained IDs and
zero replacements/closures in both variants for eligible generated names only.

## Assessment and limits

Validation: targeted fixture tests 3 passed (exit 0); offline pytest 137 passed,
14 integration tests deselected (exit 0); Ruff exit 0; compilation exit 0;
git diff --check exit 0. The parser probe completed successfully twice after
correcting its initial hash-method invocation; no product failure was inferred
from that harness error. Full synthetic measured output is stored alongside
this document. No live integration tests were run.

Workload separation is measured for alpha versus beta under the baseline.
Preserving full owner identity is the proposed future guarantee, subject to
trusted provenance and hash collision limitations. Simply dropping names or
stripping arbitrary final hyphen segments is rejected. Kubernetes truncation
and custom names prevent a universal name-only proof.

Recommendation: gather producer/provenance evidence and maintainer agreement on
ambiguous custom names before implementing a scoped application patch. The
parser defect mechanism is established; abandoning the issue is not warranted.
No upstream submission, push, cleanup or live lifecycle operation was performed.
