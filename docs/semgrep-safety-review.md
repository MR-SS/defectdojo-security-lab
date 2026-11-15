# Milestone 4E: private safety review and derived mechanism control

## Provenance and scope

The user-supplied starting reference was 39 characters, not a full 40-character
SHA. HEAD was verified as the preceding Milestone 4D commit; no supplied identifier
was repaired or used as an implicit checkout command. No external network requests,
live imports/reimports, database mutations, settings changes or cleanup occurred.

Original checksums were recalculated and matched the private download manifest.
Original directory mode 0700; original files mode 0600, owned by the current user,
not symlinks, no extended access ACL on either file. Originals remain outside the
repository, unchanged. This does not protect against root or backups and scratch
storage remains subject to cache expiry.

## Sanitized review

Each report has one previously flagged string with THREE password-assignment
pattern matches (the earlier scan counted matching strings, not individual matches).
Locations (zero-based JSON array indices):

- initial: runs[0].results[128].locations[0].physicalLocation.region.snippet.text
- changed: runs[0].results[127].locations[0].physicalLocation.region.snippet.text

Category: quoted password-like assignment in source snippet. No environment lookup
or example/sample/test/dummy/placeholder wording detected in that snippet. It is
not rule-definition text. High confidence in source-snippet classification;
credential validity, purpose and sensitivity unresolved. Could still be test code;
there is insufficient evidence to clear it. No suspected values were printed.

Each report also has one email-like string, 2348 URL-containing strings, and
143/142 snippet strings. Bounded checks found zero private IPv4 strings, zero
.local/.internal/.corp hostname strings and zero selected repository-provenance
metadata keys. These are heuristic counts, NOT proof of absence of private
repositories, organizations, public-looking internal hosts or personal information.
Source paths/code may reveal project details even without explicit provenance keys.
External references were not followed; original content is not cleared for import
or display and no claim of harmless downstream integrations is made.

Private sanitized review evidence:
`/home/sajjad/.hermes/cache/scratch/semgrep-original-14205/private-review-summary.json`.
No original content or private evidence is committed.

## Recommendation: derived-sanitized

Use a mechanism-derived synthetic pair, not the originals. The generator never
reads original content. It preserves measured cardinalities and the constant raw
fingerprint value `requires login`, but replaces all messages, rule identifiers,
paths and other content with synthetic data. There are 30 synthetic rules, 143
unique finding messages/locations, and one designated removed finding (index 1).
Rule frequency and original location sharing are NOT preserved. This tests the
observed UID-collision/removal mechanism, not byte-identical original reproduction.
No snippets, emails, network URLs or source-derived identifiers are retained.

Tracked fixtures:
- fixtures/semgrep-derived-initial.json
- fixtures/semgrep-derived-changed.json

Generator: lab/semgrep_derived.py. Unit test checks deterministic exact bytes,
143/142 results, 142 exact retained results, distinct finding text and 30 rules.
Pinned parser-only execution returned 143/142 findings, one raw UID collision group
covering every row, all effective UIDs null, and 143/142 distinct hashes.
Exactly 142 hashes retained, one removed, zero added; no hash collisions.
Derived checksums are separate from original checksums and are reported with the
execution results; regenerate with sha256sum on the tracked fixture pair.

## Pagination correction required (documented, not implemented)

Existing tests/integration/test_sarif_identity.py:115-118 fetches limit=100 once.
It is NOT ready for 143 findings. Do not merely raise the limit and assume a server
will honor it. Before live approval, implement a bounded collector:

1. Request fixed local findings endpoint with test ID, limit=100, offset=0 and
   deterministic ID ordering. Do not filter by active or mitigated state.
2. Save each page/status independently; enforce unchanged count across pages.
3. Validate every row belongs to the target Test; reject duplicate IDs.
4. Advance offset by actual returned rows; reject empty pages while next is present.
5. Do not follow arbitrary absolute next URLs with credentials. Use locally
   constructed queries and validate expected next pagination shape if used.
6. Stop only with next absent AND accumulated unique IDs equal advertised count;
   cap page count and total rows. Fail closed on truncation, loops or count drift.
7. Test 100+43 pages, empty page, duplicate ID, wrong Test, count drift, unexpected
   next URL and timeout. No automatic retries. Feed the complete aggregate into
   normalization and lifecycle comparison; never claim success on a partial page.

## Separate approval prerequisites

Prepare a dedicated exact SEMGREP-14205-DERIVED opt-in test (not implemented here),
bind tracked fixture checksums, add the above collector and a 143-record lifecycle
oracle. Require fresh source/image/parser correspondence, authenticated scope 3,
combined UID-or-hash matching, absent hash override, null service and captured
global deduplication=false; explicitly set engagement scope and disable external
pushes. No settings changes are authorized to make gates pass.

One new Product/Engagement/Test, one import (close_old_findings=false), one reimport
(close_old_findings=true, product scope=false), synchronous processing and completion
readbacks. Capture every ID, rule, UID, hash, ownership, lifecycle and duplicate flag.
Expected: original 143 IDs retained, 142 active unchanged, one absent hash mitigated,
zero new/replaced/reactivated/duplicate findings. Record persisted UID independently.
No retries, cleanup or unrelated mutations. Obtain separate live approval only after
test preparation and offline validation. Original-private import remains uncleared.
