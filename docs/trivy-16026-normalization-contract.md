# Milestone 5B — ReplicaSet normalization contract

Decision: request maintainer clarification before a default parser patch. Offer
explicit opt-in, producer-enriched identity as the safe narrow alternative.
Name-only normalization cannot guarantee absence of cross-workload merges.
This milestone changes research documentation only, not application behavior.

## Evidence scope and provenance

Lab starting commit: e20e8b2591b57bedfe9047ad5ff713f3236282ae.
Pinned DefectDojo remains 3.5.101. See the 5A reproduction and captured parser
results for measured three-handler churn; this milestone does not rerun imports.

Issue #16026 explicitly identifies telekom-mms/trivy-dojo-report-operator,
DefectDojo 2.58.4 and VulnerabilityReport. It does NOT specify either operator's
version, configuration, raw report, or transformation script. Consequently the
exact incident producer bytes and metadata are unavailable. Current source
inspection below establishes capabilities, not the incident's deployment.
Issue was open with zero comments at retrieval. PR #16028 was closed; its review
requested changes and the final comment says Closing as stale.

Repositories were inspected through GitHub's public contents API, pinned to:

- telekom-mms/trivy-dojo-report-operator: e3db91b5ad9be3abd9c1c87620acca65cbbf6936
- aquasecurity/trivy-operator: 689215dd79a7a6115b053ffb262086f3ad401656

Exact source references (paths and line numbers at those commits):

1. Forwarder src/handlers.py:266-280 copies the entire report body, including
   metadata; :284-293 optionally replaces it with transformation output;
   :318-322 resolves configurable request service; :352-355 serializes the body;
   :398-417 includes service in API data; :432-440 posts reimport-scan.
   Nothing in this forwarding path resolves a ReplicaSet's Deployment ancestor.
   A transformation can enrich metadata, but is arbitrary user configuration,
   not a guaranteed producer contract. Current service override support also
   contradicts a universal reading of the issue's no-override assertion.
2. Trivy pkg/apis/aquasecurity/v1alpha1/vulnerability_types.go:133-135,
   config_audit_types.go:34-36, exposed_secrets_types.go:55-57 embed ObjectMeta.
   Ability to represent annotations/ownerReferences is not a guarantee of
   Deployment ancestry or any particular user label.
3. pkg/vulnerabilityreport/builder.go:380-425 sets container, optional spec hash,
   configured copied/custom labels, resource identity and a controller reference.
4. pkg/configauditreport/builder.go:127-171 sets resource identity, configured
   labels, optional spec/config hashes and controller reference; it does not
   supply a container label in this path. Checks can be resource-scoped.
5. pkg/exposedsecretreport/builder.go:77-117 sets container, optional spec hash,
   configured labels, resource identity and controller reference.
6. pkg/kube/object.go:139-175 encodes resource kind and namespace, with name in
   a label when label-valid; otherwise a resource-name-hash label and original
   resource name annotation. :405-443 resolves Deployment/Pod to ReplicaSet and
   returns ReplicaSet itself. The report owner is that ReplicaSet, not its parent.
7. pkg/kube/labels.go:4-9 copies only configured resource labels; :13-16 copies
   configured custom labels. Thus pod-template-hash can be carried if configured
   and present, or even supplied as a custom label; it is not mandatory proof.
8. Kubernetes naming sources already inspected in 5A: v1.35.0
   pkg/controller/controller_utils.go:1395-1406 (encoded decimal FNV32a hash),
   pkg/controller/deployment/sync.go generateReplicaSetName (possible truncation),
   apimachinery v0.35.0 pkg/util/rand/rand.go:121-126 (SafeEncodeString).
   resource-spec-hash is NOT interchangeable with Kubernetes pod-template-hash.

No report-embedded URLs were followed, and no Kubernetes API was queried.

## Metadata availability

| Information | Producer behavior | Safe parser inference |
|---|---|---|
| Resource kind/namespace | Explicit identity labels in builders | Use after validation; do not confuse report kind with resource kind |
| Resource name | Label, or original-name annotation fallback | Name-hash is not reversible; report object's name may also be hashed |
| Container | Vulnerability/secret builders supply it | Preserve; checks may legitimately lack it |
| ownerReferences | Reference to scanned controller, commonly ReplicaSet | Does not include transitive Deployment ancestry |
| pod-template-hash | Configurable copied/custom label | Optional corroboration, not proof of ownership |
| Resource annotations | Report annotations supported; original-name fallback and TTL shown | Arbitrary workload annotations are not guaranteed copied |
| Stable Deployment parent | Not supplied by the examined default paths | Requires explicit producer enrichment or external knowledge |
| Truncated Deployment name | Original ReplicaSet name may be available | Full pre-truncation parent name cannot be reconstructed from it |

Reading the ReplicaSet and its controller reference through Kubernetes would
provide ancestry to a trusted producer. That lookup is outside a standalone
report parser and was not performed here. Exported metadata is input, not
cryptographic attestation; the trust boundary remains the report producer.

## Normalization decision table

| Strategy | Entry conditions | Outcome | Merge/split tradeoff |
|---|---|---|---|
| A: provenance-backed | Explicit validated binding of this ReplicaSet identity to one Deployment in same namespace, full parent name; contradictions absent | Canonical parent-qualified identity | Avoids heuristic merges under trusted binding; missing evidence preserves rollout splits |
| B: hash corroboration | Exact terminal suffix equals reported pod-template-hash, valid encoding, nonempty prefix | Corroboration only; no automatic default normalization without A | Custom names and labels can imitate it; truncated prefixes can merge unrelated owners |
| C: opt-in name heuristic | Operator knowingly selects a scoped heuristic for known Deployment-only input | Strip only validated suffix, preserve full prefix; reject uncertain/truncated cases | Reduces splits but cannot exclude custom-name collisions; not safe as an unconditional default |
| D: preserve original | Default; missing, conflicting, malformed or unsupported provenance; custom ReplicaSet | Return unchanged identity with reason | No new normalization-induced merges; existing rollout splits remain |

All strategies leave non-ReplicaSet identity unchanged. Hyphens inside the full
parent name are preserved. A consumes full owner identity rather than guessing
at the last hyphen. B/C cannot recover truncated parent identity. Missing
namespace/container must not be guessed: missing namespace blocks A; absent
container stays absent for resource-level findings. Conflicting name label and
annotation, owner identity or hash evidence forces D, not precedence guessing.

## Desired identity and collision analysis

Proposed semantic tuple for A:
(namespace, resource_kind='ReplicaSet', identity_class='Deployment',
 full_deployment_name, container_or_absent).

Proposed service serialization:
namespace/ReplicaSet/@Deployment/full-deployment-name[/container]

The explicit reserved identity-class segment is important. Merely replacing
`alpha-HASH` with `alpha` could collide with a custom ReplicaSet named alpha.
The proposed marker contains a character invalid in Kubernetes resource names,
so validated raw names cannot occupy the same identity class. This is a new
format proposal requiring maintainer agreement, not existing DefectDojo syntax.
Keep raw names for unchanged/custom inputs. Do not relabel the resource kind to
Deployment: a directly scanned Deployment remains a different resource kind.
Validate Kubernetes name components; never accept slash-delimited arbitrary
strings as validated identity components.

Description: keep resource.kind ReplicaSet and use the same tagged canonical
resource.name (`@Deployment/full-deployment-name`) used for identity. Namespace
and container text remain intact. Do not append the volatile original ReplicaSet
name elsewhere in the hashed description. Raw generation details, if retained,
need a non-hash-bearing location and separate design; no storage change now.

This distinguishes different parents, namespaces, containers and raw custom
ReplicaSets. It does not distinguish clusters with identical namespaces/names;
require separate Test/Engagement or other explicit cluster scope. Parent deletion
and recreation under the same name intentionally continues name-based identity;
UID-based lifetime separation is a separate policy. Cryptographic hash collisions,
untrusted forged provenance and inaccurate producer bindings are not ruled out.

A pure suffix recognizer cannot solve this: independent custom alpha-HASH1 and
alpha-HASH2 collapse to alpha, even if both carry matching hash labels. Two long
Deployment names with the same truncated prefix are another counterexample.
The safe design must not claim these are distinguishable from report name alone.

## Proposed helper interface (design only)

resolve_replicaset_identity(*, namespace, resource_kind, resource_name, container,
                           deployment_binding=None, pod_template_hash=None,
                           mode='preserve') -> IdentityResolution

IdentityResolution contains canonical components, changed boolean and reason.
DeploymentBinding is a proposed typed producer contract, not an existing report
field: source ReplicaSet name/namespace/UID, parent kind/name/namespace/UID,
controller relation, provenance format/version. Require consistency with report
identity and its ReplicaSet owner reference; reject absent or competing owners,
wrong kind, wrong namespace, incomplete/truncated parent names and conflicting
hash data. Validate supported naming relation when present; do not infer a
binding from it. No I/O in helper. Caller must explicitly select the trusted
producer contract; arbitrary extra annotations do not activate normalization.

Modes: preserve (default), verified-parent (A), optional documented heuristic
(C, only if maintainers accept residual risk). B is a validation input, not an
authorization switch. Heuristic mode cannot satisfy the full safety promise and
must not silently activate for existing users. The 5A minimal fixtures lack
binding evidence and therefore remain unchanged in preserve/verified-parent modes.

## Hash, matching, closure and migration

5A measured hash_code fields: title, severity, vulnerability_ids, description;
service is always included. Canonical service plus canonical description gives
stable hashes across eligible generations when all other fields are unchanged.
Changing only request service cannot remove a resource.name change in description.

Canonicalization changes previously stored hashes/services. Existing records are
not rewritten by a parser patch. First normalized reimport can create replacements
rather than match old findings. Do not introduce fuzzy legacy fallback matching:
it could reconnect independent custom workloads. No automatic backfill/cleanup.
An opt-in rollout should document a separately approved migration or fresh Test,
record old/new identity maps and account for duplicate historical generations.
Disabling normalization later can cause another identity discontinuity.

Pinned default_reimporter.py:326-328 scopes closure by request service (null/empty
when omitted), :1038-1041 matches hashes, :1262-1341 handles active matches.
Parser normalization alone does not fix closure scope: omitted request service
still excludes nonempty parser services. With a stable explicit request service,
legacy and new records may be eligible for closure but hashes still differ at
migration. Different old request services leave old records outside that scope.
No persisted lifecycle behavior was tested in 5B. Maintain the separate future
experiments in trivy-16026-reproduction.md; do not infer closure from hash tests.

## Regression specification (not implementation or passing test claim)

Use each existing fixtures/trivy-{vulnerabilities,checks,secrets}-{initial,changed}
pair, deep-copying only metadata for enriched variants. Keep original fixture
bytes unchanged. Run the real parser/hash method on unsaved findings. Do not use
a test-only normalization implementation as evidence of application correctness.

| Case | Setup | Required oracle for every handler |
|---|---|---|
| Same parent / two generations | Add consistent proposed binding for alpha to both 5A generations | Two findings each; alpha equal service/description/hash; beta separate |
| Independent parents | Alpha and beta, same namespace/container and identical security entry | Distinct services, description identity and hashes; stable per parent |
| Namespace separation | Same parent name, two namespaces | Distinct hashes/services, including stable request-service override control |
| Container separation | Same parent, app versus worker | Distinct services/hashes; absence remains distinct from named container |
| Custom hash-shaped names | No parent binding; names imitate generated pair; optional matching hash label | Names unchanged by default; no false claim B proves ancestry |
| Raw/custom versus canonical | Custom ReplicaSet alpha beside verified parent alpha | Distinct identity classes/services/hashes |
| Missing/conflicting metadata | Missing owner; wrong kind/namespace; multiple parents; mismatch name/UID/hash; label/annotation conflict | Preserve original, reason populated; no partial normalization |
| Stable/non-ReplicaSet | Custom alpha, hyphenated stable name, Deployment, StatefulSet, Job, Pod | Original behavior unchanged |
| Hyphenated parent | Parent alpha-api-worker, two valid generations | Entire parent retained, stable identity |
| Truncation | Long parents sharing truncated prefix; full bindings versus absent binding | Distinct full-parent identities with A; unchanged without evidence |
| Annotation fallback | Missing resource-name label, valid original-name annotation; hash-only variant | Explicit validated decoding policy; never strip name-hash; unresolved input unchanged |
| Trust/mode boundary | 5A originals and forged arbitrary enrichment, preserve mode | No normalization; verified mode requires recognized binding contract |
| Migration | Legacy captured hashes versus canonical output | Explicit expected hash change, not assertion of old ID retention |

Checks ordinarily lack container data from producer; cover both absent-container
checks and the synthetic 5A supplied-container case. Add zero/one/many findings
and unsupported metadata type tests when implementing. Lifecycle ID/closure
assertions require separate approval and are not offline acceptance criteria.

## Upstream readiness

PR #16028 review requested: bugfix target, keep workload name, strip only
ReplicaSet suffix in all three handlers, normalize description too, and test
ReplicaSet/non-ReplicaSet plus workload separation. It also corrected request
service versus parser service. Those identity-preservation goals are met by A
for eligible enriched reports, but default real reports do not provide A's
ancestry, and the reserved parent-qualified serialization goes beyond the
requested simple suffix strip. This is not implicit maintainer approval.

Recommendation: request clarification before coding. Present the custom-name
and truncation counterexamples and ask whether maintainers prefer (1) documented
opt-in heuristic with acknowledged risks, or (2) explicit producer enrichment
contract and parent-qualified identity. Prefer (2) for collision safety. Ask for
actual operator versions and a sanitized metadata-only report from the incident;
none was provided by the issue. Current forwarder transformation hooks can support
an enrichment path, but availability in the incident version is unknown.

No upstream contact, push, application edits, imports, database mutations,
Kubernetes requests, infrastructure changes or cleanup occurred.

## Offline validation

Offline pytest: 137 passed, 14 integration tests deselected (exit 0).
Ruff: exit 0. Python compilation: exit 0. git diff --check: exit 0.
Existing fixtures, lab code and tests unchanged against the starting commit
(git diff --exit-code: 0). New regression cases above are specifications, not
implemented normalization tests. This documentation-only milestone does not
claim new runtime parser or lifecycle measurements.
