# SARIF #14205: final evidence-bounded assessment

## Scope and pinned environment

DefectDojo 3.5.101, source SHA 32aea6841a019b050737c8874b939b236095333e.
Dedicated ddslab instance, Product Type 3. Combined
unique_id_from_tool_or_hash_code matching, global deduplication disabled, null
service, no configured SARIF hash override/custom method, always=[service].
These results apply to that configuration, not every possible SARIF deployment.

## Reviewed completed evidence

All five saved summaries and import/reimport responses were re-read. Every pair
returned HTTP 201/201 with sync processing and deduplication_complete=true.
Every scenario preserved its exact initial database ID set and Test ownership;
all stored hashes stayed stable; no duplicate flags or reactivations appeared.

| Scenario | Test | Original/final IDs | Initial active | Final active/mitigated | Reimport new/closed/unchanged |
|---|---:|---|---:|---|---|
| S1 unique fingerprint, line move | 8 | 22 | 1 | 1/0 | 0/0/1 |
| S2 shared fingerprint, identical reimport | 9 | 23,24 | 2 | 2/0 | 0/0/2 |
| S3-A unique fingerprint removal | 10 | 25,26,27 | 3 | 2/1 | 0/1/2 |
| S3-B collision-sensitive removal | 11 | 28,29,30 | 3 | 2/1 | 0/1/2 |
| SEMGREP-14205-DERIVED | 12 | 31 through 173 | 143 | 142/1 | 0/1/142 |

Closed rows: S3-A ID 26; S3-B ID 29; derived ID 32 (ddslab/rule-01).
The derived readbacks each comprised 100+43 rows, matching count=143 and ending
with no next page. The oracle compared hash/rule mappings as well as ID sets.

S1 submitted line 10 then 11 but stored main Finding line remained 10, with its
original hash and UID. The earlier read-only associated-location check found
locations enabled but zero LocationFindingReference rows for Finding 22. This is
not proof about historical transient records or a general location-reconciliation
contract. It is separate from the successful identity/lifecycle control.

S2 raw shared UIDs were cleared; persisted UIDs stayed null. S3-B rule-0's incoming
UID became unique after removal, but its persisted UID stayed null and its unchanged
hash preserved ID 28. S3-A UIDs stayed unique. Derived raw UID was the constant
'requires login' on all rows; effective and persisted UIDs were all null.

Private local evidence directories (not committed):
- evidence/ddslab-sarif-8cc7de9984a9491780491fc2499f1c5f (S1)
- evidence/ddslab-sarif-d03a9ae1fc8f4877b998385f8629ff0a (S2)
- evidence/ddslab-sarif-35dc9de99b0947e0a467f7b41226493a (S3-A)
- evidence/ddslab-sarif-7b85cf648d6f4078b621fb5c454f7121 (S3-B)
- evidence/ddslab-semgrep-derived-dbb52e77d77b4dca8b01710ce5e87d9a

## Original versus derived reports

Original Semgrep attachments were downloaded and inspected/parser-tested privately,
NEVER imported into the application. Their 143-to-142 transition was verified by
complete result-object multiset comparison. All raw fingerprints were the constant
placeholder, all effective UIDs cleared, hashes distinct, 142 unchanged retained
hashes. Safety review left source snippets/password-like content uncleared.
No sensitive source material is included here.

Derived fixtures replace source content, paths and rules with synthetic data.
They preserve cardinality, shared-UID ambiguity, unique hashes and exact one-result
removal, not original bytes, rule frequencies or shared-location distribution.
They demonstrate the mechanism control, not byte-identical original reproduction.

## PR #15817 and conclusions

The repeated-UID mitigation is present in pinned parser/importer source:
dojo/tools/utils.py:129 onward; dojo/importers/base_importer.py:397-418.
DefaultReImporter:1038-1079 builds UID/hash candidates; :592 computes unmatched
closure candidates. Clearing placeholder UIDs permits distinct retained hash matches.
The observed results are consistent with this mitigation, not a causal before/after
proof that this PR alone fixes every report.

Demonstrated: these five controls retain intended identities and close only the
absent finding under the tested configuration. The derived mass-closure mechanism
did NOT reproduce the reported erroneous outcome on 3.5.101.

Unproven: historical 3.1.0 behavior, original-attachment live behavior, global-dedupe
on configurations, UID-only matching, arbitrary scanner fingerprints, all image/
location combinations, other versions, performance/scale and every variant of #14205.
Each live scenario was executed once; none is a replicated benchmark.

Decision: no new upstream SARIF bug report is justified by these results. A narrowly
worded evidence contribution to the existing discussion could be useful only with
separate approval; do not declare the issue universally fixed or close it on behalf
of maintainers. No upstream submissions were made.
