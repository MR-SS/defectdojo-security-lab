# close_old_findings endpoint semantics — DefectDojo 3.5.101

Source inspected: DefectDojo tag `3.5.101`, commit `32aea6841a019b050737c8874b939b236095333e`.

## Endpoint paths

The v2 serializers independently select their handlers:

- `/api/v2/import-scan/` uses `ImportScanSerializer`, which constructs `DefaultImporter` (`dojo/api_v2/serializers.py:721-795`; shared handler `:574-612`). `DefaultImporter.create_test()` creates a fresh target Test (`dojo/importers/default_importer.py:65-91`); its `process_scan()` parses, processes findings, then calls its import-specific `close_old_findings` (`:93-125`).
- `/api/v2/reimport-scan/` uses `ReImportScanSerializer` and selects `DefaultReImporter` only when a target Test is resolved (`dojo/api_v2/serializers.py:798-956`, especially `:896-903`). Its `process_scan()` computes target-Test original items, matches incoming entries, then invokes its reimport-specific `close_old_findings` with those unmatched target-Test items (`dojo/importers/default_reimporter.py:96-145`, `:310-328`, `:592-608`, `:869-916`). If auto-create finds no Test, it intentionally falls back to `DefaultImporter` with `close_old_findings=False` (`dojo/api_v2/serializers.py:904-916`).

## Exact import semantics

For a regular import, `close_old_findings` defaults false (`dojo/api_v2/serializers.py:729-745`). When explicitly true, the importer’s `get_close_old_findings_queryset()` starts with active or risk-accepted Findings of the same Test type, explicitly excludes the newly created target Test, then limits candidates to the same Engagement by default or Product when `close_old_findings_product_scope=true` (`dojo/importers/default_importer.py:378-420`). Thus a new T2 import can close qualifying old findings in T1 or another sibling Test, but cannot close rows newly created in T2.

Candidates whose identity is present in the incoming non-mitigated report are excluded using the resolved reimport-deduplication algorithm: hash/legacy uses hash; `unique_id_from_tool` uses the UID; the combined algorithm accepts either non-null match (`default_importer.py:392-409`, `:439-450`). A service input restricts candidates to exactly that service; an absent service restricts to null/empty-service findings (`:415-419`). The toggle is the first guard (`:422-486`). The implementation mitigates selected rows and their locations (`:427-471`). Existing inactive non-risk-accepted rows are not initial candidates; report entries already marked mitigated do not protect identities from closure (`:439-450`).

## Exact reimport semantics

For a reimport with an existing Test, `close_old_findings` defaults true (`dojo/api_v2/serializers.py:813-828`). Its scope is the target Test, not Engagement/Product: `get_original_findings()` loads only `self.test.finding_set`, restricted to matching service or null/empty service (`dojo/importers/default_reimporter.py:310-328`). After matching, `to_mitigate` is target-Test original IDs minus reactivated and unchanged items (`:592-608`), and the reimport close method only receives those IDs (`:137-145`, `:787-818`, `:869-916`). Therefore `close_old_findings_product_scope` has no reimport effect despite being accepted (`serializers.py:824-828`).

A matching closed finding reactivates unless `do_not_reactivate=true`; special triage states (false positive, out of scope, risk accepted) follow separate protected handling (`dojo/importers/default_reimporter.py:1090-1112`, `:1150-1260`). A candidate already mitigated by an earlier reimport transition is not mitigated again (`:890-916`).

Synchronous versus asynchronous deduplication controls post-processing dispatch completion, not the endpoint’s candidate scope. The serializer resolves a requested mode against the user preference (`dojo/api_v2/serializers.py:710-716`). `async_wait` records and awaits dispatched post-processing before final accounting (`dojo/importers/default_reimporter.py:175-177`, `:780-785`); `sync` runs inline; ordinary async can leave post-processing unfinished at response time. Close-old selection/mutation occurs in the importer transaction path before that wait.

## Documentation comparison

Pinned reimport documentation says closure is limited to the target Test and honors service, while import may operate at Engagement/Product scope. See `docs/content/import_data/import_intro/reimport.md:42-64`, especially `:51-53`; serializer help text independently says the same (`dojo/api_v2/serializers.py:729-745`, `:816-828`). There is no conflict in 3.5.101: apparent contradiction comes from applying Import documentation/handler behavior to Reimport. The previous ambiguous analysis incorrectly generalized the import query to reimport; source tracing distinguishes them. No implementation discrepancy or bug is claimed.

## Scenario R1 — same-Test reimport

Separate Product and Engagement; no service (therefore null/empty-service scope); Generic Findings parser and `deduplication_execution_mode=sync`. The identity fixture preserves A/C UIDs and omits B.

1. Import T1 with A, B, C.
2. Reimport the same T1 with A, C, `close_old_findings=true`, `close_old_findings_product_scope=false`, `do_not_reactivate=false`.

Expected: T1 A/C remain matched and active; T1 B becomes inactive and mitigated. No sibling Test is eligible. The test fixtures pin UIDs; the actual resolved reimport algorithm must be recorded as a runtime precondition in any approved run because the API request does not set it. A non-UID algorithm could change matching behavior and must be classified INCONCLUSIVE, not silently accepted.

## Scenario I1 — cross-Test import

Separate Product and Engagement; no service; same scan type; synchronous post-processing. Identity fixture is identical to R1.

1. Import T1 with A, B, C, with close-old requested (nothing prior in the new Engagement).
2. Import new T2 with A, C and `close_old_findings=true`, `close_old_findings_product_scope=false`.

Expected: T2 contains A/C. Import closure considers same-Engagement, same-type T1 candidates and excludes T2. T1 A/C are protected by incoming identity comparison; T1 B is mitigated/inactive. Product scope must remain false so no other Engagement is eligible. As in R1, record the resolved algorithm and classify mismatch/inadequate configuration evidence as INCONCLUSIVE.

For both: capture sanitized HTTP summaries, Product/Engagement/Test IDs, exact fixture checksums, resolved deduplication settings, service scope, normalized per-Test findings before/after, closed/reactivated/untouched counts, and post-processing completion. Never clean up automatically.

## Approval-gated commands

Do not run these until a separate mutation approval:

    DDSLAB_RUN_INTEGRATION=1 DDSLAB_RUN_R1=1 \
      DDSLAB_API_BASE_URL=http://127.0.0.1:18080 \
      DDSLAB_API_TOKEN=... DDSLAB_PRODUCT_TYPE_ID=... \
      .venv/bin/pytest -q tests/integration/test_close_old_findings.py -k r1

    DDSLAB_RUN_INTEGRATION=1 DDSLAB_RUN_I1=1 \
      DDSLAB_API_BASE_URL=http://127.0.0.1:18080 \
      DDSLAB_API_TOKEN=... DDSLAB_PRODUCT_TYPE_ID=... \
      .venv/bin/pytest -q tests/integration/test_close_old_findings.py -k i1
