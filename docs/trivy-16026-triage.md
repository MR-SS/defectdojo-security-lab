# Next contribution triage: Trivy Operator #16026

## Current upstream evidence

GitHub API was queried during this assessment, not inferred from historical status.
Issue #16026 is open, with zero comments. Its complete timeline links PR #16028.
PR #16028 is CLOSED, NOT MERGED, and its review requested changes; it was later
closed as stale. No replacement was identified by searches across all PR states
for '16026', 'ReplicaSet', and 'trivy operator'. Search returned complete results
(37 Trivy Operator matches, one ReplicaSet match); this is bounded discovery, not
proof that no differently worded future work exists.

Relevant merged PRs include #15999 (image locations), #16245 (image deduplication
documentation), #14360 (metadata mappings), and #10389 (hash configuration). None
of those titles or the pinned handlers establishes ReplicaSet normalization.

Sources:
- https://github.com/DefectDojo/django-DefectDojo/issues/16026
- https://github.com/DefectDojo/django-DefectDojo/pull/16028
- PR reviews API: /repos/DefectDojo/django-DefectDojo/pulls/16028/reviews

## Maintainer guidance and proposed-fix limitations

The review explicitly distinguishes request service from parser service. It asks
for targeting bugfix, retaining workload name while stripping only a ReplicaSet
pod-template-hash suffix, and using the same normalized name in the description.
It asks for ReplicaSet, Deployment/StatefulSet, and distinct-workload tests.

The abandoned proposal dropped resource_name entirely. That merges namespaces/
kinds/containers across different workloads and leaves description volatility
unfixed. Reimplementing that proposal unchanged is not an acceptable contribution.

## Exact pinned behavior (3.5.101)

The unnormalized name is still used by all three handlers:
- dojo/tools/trivy_operator/vulnerability_handler.py:23-29,78-81
- dojo/tools/trivy_operator/checks_handler.py:16-22,39-40
- dojo/tools/trivy_operator/secrets_handler.py:23-29,46-47

Service is namespace/kind/name[/container]. Description embeds resource.name.
Observed effective Trivy Operator matching is hash_code; configured hash fields
are title, severity, vulnerability_ids, description; always-included field service.
Thus a rollout-only name change changes two identity inputs even when vulnerability,
image and logical workload are unchanged. This remains a specific source-supported
candidate, not a live-verified lifecycle defect.

Related pinned tests in unittests/tools/test_trivy_operator_parser.py cover zero/
single/multiple reports, severity/CVE/package mappings, additional fields, image
locations and report containers. The inspected test list has no rollout-name
normalization/regression test; vulnerability tests :47-85 assert counts and fields,
not stability across names.

## Closure claims corrected

DefaultImporter:416-419 filters old findings by REQUEST service, or only null/empty
services when omitted. DefaultReImporter:326-328 independently does the same for
original findings in the selected Test. Parser-generated service does not assign
self.service. Both paths permit an explicit request override:
DefaultImporter:257-258, DefaultReImporter:401-402 overwrite parser service when
request service is non-None. The issue's claim that callers cannot override is
therefore incorrect on this pinned version.

Omitted request service + nonempty parser services can exclude old rows from
closure even with an unchanged resource name. Volatile names additionally alter
matching hashes; normalization alone does not repair the omitted-service closure
contract. Stable request service makes closure scope stable but description can
still change hashes. Do not combine new-Test import and same-Test reimport into
one unqualified explanation. Do not weaken service isolation globally.

## Recommendation: bounded reproduction, not a new issue yet

Proceed first with a synthetic parser-only rollout control, followed by separately
approved same-Test lifecycle experiments if necessary. No production reports,
Kubernetes deployment or live experiment is needed to establish parser volatility.

Smallest identity control: two otherwise identical synthetic VulnerabilityReports,
one vulnerability each; only ReplicaSet resource.name suffix changes. Keep image
identity/package/version/namespace/container stable to avoid confounding image
matching. Assert original behavior changes service AND description/effective hash.
Use two independent workloads to ensure a proposed fix does not merge them.

Smallest closure control: initial A+B and changed A, same workload. Compare separate
isolated scenarios with omitted request service versus explicit stable request
service; also hold the resource name fixed in a control. This separates closure
selection from name-derived hash churn. A deployment/name-only variant must not
be presented as fixing the missing-service contract.

Likely acceptable change: small shared ReplicaSet-only name-normalization helper
used consistently in service and description across vulnerability/check/secret
handlers, preserving distinct workload names and non-ReplicaSet names. Follow the
review, but specify recognized suffix syntax and behavior for ambiguous/custom
ReplicaSet names before coding; blindly truncating the last hyphen segment risks
collisions. Document request-service override and closure semantics separately.
Existing persisted hashes/services can change on upgrade: document compatibility
and do not auto-migrate records.

Expected regression tests: same workload two suffixes => same normalized service,
description and effective hash; distinct workloads => distinct identities;
Deployment/StatefulSet/custom/no-suffix names unchanged; namespace/container
separation; all three handlers; missing labels; unchanged image identity;
request-service override precedence; closure with omitted versus stable service;
no unrelated service closure; old/new hash compatibility expectations.

Before an upstream patch: recheck current bugfix branch at an immutable SHA and
search status again, get agreement on suffix semantics, reproduce failing tests
and pass parser/importer suites. No specific alternate issue is better supported
by this investigation. No new report, live experiment or upstream submission is
authorized by this recommendation.
