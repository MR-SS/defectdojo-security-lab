# Milestone 4C: SARIF collisions and removal

No live imports performed. S1 evidence confirms Finding 22 in Test 8 remained
active at main-field line 10. A read-only model query found locations_enabled=true
but zero LocationFindingReference rows through Finding.locations for Finding 22.
There is therefore no evidence that line 11 was persisted as an associated
location for S1. This is a current-state observation, not proof about historical
transient records or all location backends.

Issue 14205 discussion distinguishes CodeQL rule/fingerprint collisions from
later Semgrep partial removal. PR 15817 is merged and included in the pinned
3.5.101 source. See sarif-14205.md for the verified issue/PR status. We do not
assume the latest large-report case has the same root cause.

## Identity layers and source

SARIF parser get_items_from_result creates separate findings for separate
results/locations and copies the fingerprint without rule ID namespacing.
get_findings/get_tests mark identities potentially ambiguous.
dojo/tools/utils.py:129+ removes repeated IDs only when invoked after parsing;
dojo/importers/base_importer.py:414-418 performs grouping then ambiguity removal.
Raw parser UIDs must not be confused with effective importer UIDs.
DefaultReImporter :1038-1081 unions UID and hash matches; :1328 tracks unchanged
active matches. :592 subtracts unchanged/reactivated IDs from original items to
choose closure candidates. This is distinct from global deduplication, which can
mark duplicates across findings; capture duplicate flags and effective settings
before live execution. No global setting is changed by the prepared tests.

## Fixtures and exact expected states

S2: two rules, distinct messages, same location and fingerprint. Both raw parser
rows survive, both effective UIDs become null, and distinct message/title content
produces distinct hashes. Identical reimport should preserve two active,
unmitigated, nonduplicate IDs. Distinct rule IDs alone do not guarantee distinct
legacy hashes; these fixtures deliberately include distinct vulnerability text.

S3-A: three unique fingerprints; remove rule-1 only. Three persisted IDs should
remain, rule-1 inactive/mitigated and rule-0/rule-2 active, no new IDs or duplicates.

S3-B: rule-0/rule-1 share a fingerprint, rule-2 is unique. Initially the first two
UIDs are dropped. Remove rule-1 only: rule-0's incoming UID becomes unambiguous,
but its hash is unchanged and should match the existing null-UID row through
the OR algorithm. Only rule-1 should close. Persisted UID reconciliation is
observed independently, not forced. No location changes are combined with removal.

Actual parser-only validation on all six tracked fixtures returned cardinalities
2/2, 3/2, 3/2 and the UID transitions above; exit 0. No saves or importer writes
were called. Effective hashes for rules 0/1/2 were distinct and stable across
retention. Tracked byte generation and negative lifecycle oracles have offline tests.

## Execution boundary

Existing tracked tests/integration/test_sarif_identity.py now accepts separately
selected S2, S3-A, S3-B. Each requires exact DDSLAB_APPROVE_SCENARIO plus integration
opt-in. It loads tracked fixtures, captures raw/effective parsed IDs before any
API mutation, and uses an isolated Product/Engagement/Test in Product Type 3.
Evidence includes full API response rule IDs, normalized identities, checksums,
request flags and synchronous completion. No cleanup or automatic retry exists.

Next request: approve S2 only, with fresh authenticated readiness, pinned source/
image correspondence, effective SARIF algorithm and global dedupe observation.
Then select tests/integration/test_sarif_identity.py::test_sarif_identity[S2].
S3-A and S3-B require distinct later approvals. Parser-only success is not live
reproduction and does not justify an upstream fix or declaring issue 14205 solved.
