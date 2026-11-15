# Milestone 4D: original Semgrep pair (offline research)

## Provenance and preservation

Issue 14205 comment 4950382798 links attachments 29936031/semgrep.json and
29936033/semgrep2.json. Both downloads returned HTTP 200. Original bytes are
privately preserved outside the repository at:
`/home/sajjad/.hermes/cache/scratch/semgrep-original-14205/`.
The directory is mode 0700 and original files mode 0600. `manifest.json` records
source URLs, byte lengths and SHA-256 checksums. No report content is tracked.
Scratch storage is not permanent archival storage; preserve it before cache expiry
if a durable evidence archive is required. No originals were modified or reduced.

## Measured original distribution

Both are JSON SARIF 2.1.0 with one run. Initial: 143 results, 143 parser findings,
143 locations, 30 distinct rule IDs. Changed: 142 results, findings and locations,
30 distinct rule IDs. Multiset comparison of complete result objects confirms
142 exact retained results, one removed, zero added. There are 138 distinct
retained file/line pairs (locations are not unique finding identities).

Every result carries the same fingerprint value: `requires login`. Neither report
uses partialFingerprints. Raw parser UIDs therefore have one collision group,
covering all 143/142 rows. Pinned ambiguity removal clears every UID. Effective
hashes are all distinct (143/142); exactly 142 hashes are retained, one removed,
zero added. All parsed findings are active and not false positives. Parser-only
execution used unsaved Finding objects and no importer/save methods.

The content-free `lab.semgrep_analysis.identity_statistics` helper independently
checks hash retention and collision cardinalities. Private `analysis.json`,
`parsed.json` and `safety.json` preserve measured outputs. JSON shape and parser
compatibility were validated, not full SARIF JSON-Schema conformance.

## Pinned source and causal interpretation

Source is the pinned 3.5.101 checkout; runtime SARIF parser and ambiguity utility
bytes were compared with that checkout successfully.

- dojo/tools/sarif/parser.py: get_findings/get_tests mark ambiguous identities;
  get_items_from_result expands locations and takes fingerprints before partial
  fingerprints. The constant placeholder becomes a raw UID, not a real identity.
- dojo/tools/utils.py:129 onward clears every repeated nonempty marked UID.
- dojo/importers/base_importer.py:397-418 groups first (open-source identity
  grouping), then clears ambiguous UIDs before downstream matching.
- dojo/importers/default_reimporter.py:1038-1079 builds hash/UID candidates;
  combined matching unions both, then orders candidates deterministically.
- Same file :476 chooses matched_findings[0]; :1328 records unchanged active
  findings; :592 subtracts unchanged/reactivated IDs from original closure candidates.
- dojo/finding/deduplication.py:96-101 and :1067-1069 gate deduplication on the
  global setting. :244-247 and :432-439 constrain engagement scope, not independently
  enable deduplication. Reimport matching/closure is a separate operation.

A constant UID can make every incoming row select the same original candidate,
leaving only one original in the unchanged set and 142 closure candidates. This
is a strong input-backed explanation of the reported 3.1.0 symptom, NOT a verified
execution trace or reproduction on that historical version.

PR 15817's repeated-UID mitigation is present in pinned source. Under current
combined matching, cleared UIDs force distinct hash matches. Expected fresh-state
outcome is 142 unchanged, one closed, zero created/reactivated on reimport.
No live reproduction was performed, so the observed runtime lifecycle remains
unverified. UID-only configuration is outside this expectation: null UIDs cannot
match through the UID-only branch and must not be conflated with combined matching.

Effective read-only configuration: combined UID-or-hash, no SARIF hash-field
override, always-included service, global deduplication disabled. These observations
are not permission to change settings or reuse historical preflight indefinitely.

## Safety blocker and execution boundary

Original reports contain 143/142 source-snippet objects and 2348 strings containing
external URLs each. A bounded credential-pattern scan matched one string in each
report. This is a suspected sensitive value, not proof of a valid credential;
its value was neither printed nor tracked. No embedded links were followed and
no attached code was executed. Absence of additional regex matches is not a
comprehensive secret clearance.

Consequently the original pair is NOT yet cleared for import. No live integration
test accepting these originals was added: the requested preparation was explicitly
conditional on safety and suitability. Existing synthetic integration tests remain
unchanged. Committing originals, laundering content into synthetic fixtures, or
silently bypassing safety would invalidate provenance or risk disclosure.

## Exact gated continuation

1. Separately authorize private content safety review; establish whether the
   flagged value and source snippets can be stored in the dedicated lab. Do not
   request secrets in chat. If sanitization is required, preserve originals and
   approve a derived pair separately; re-characterize hashes after any edit.
2. Once cleared, prepare a dedicated SEMGREP-14205-ORIGINAL opt-in tracked test
   binding the exact manifest checksums. Do not use the existing 100-row findings
   fetch unchanged: paginate and enforce count/next completeness for 143 records.
3. Require fresh pinned source/image and account-scope checks; combined matching,
   null service, unchanged hash settings, global deduplication disabled and explicit
   engagement deduplication scope. Record raw/effective IDs before mutations.
4. Obtain separate authorization for one import and one same-Test reimport in a
   new Product/Engagement under Product Type 3, sync processing, closure true on
   reimport only, product-wide closure false, no retries and no cleanup.
5. Capture content-minimized per-finding evidence indexed by database ID and hash;
   require original 143 IDs retained, exactly the absent hash closed, 142 active,
   no replacements/duplicates/reactivations. Record persisted UID separately.
6. On partial failure read existing state only. No upstream submission is implied.
