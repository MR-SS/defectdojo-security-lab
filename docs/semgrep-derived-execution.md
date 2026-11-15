# Milestone 4F: derived Semgrep live preparation

No application import/reimport was executed. Original attachments are never read
by the new runner. The tracked derived pair is checksum-bound through
configs/semgrep-derived-checksums.json and checked against deterministic generation.

## Entrypoint and approval

From the repository root, ONLY after separate live authorization:

    DDSLAB_RUN_INTEGRATION=1 DDSLAB_APPROVE_SCENARIO=SEMGREP-14205-DERIVED DDSLAB_SOURCE_CHECKOUT=/home/sajjad/.hermes/cache/scratch/ddslab-upstream/3.5.101 .venv/bin/python -m pytest tests/integration/test_semgrep_derived.py::test_semgrep_derived -q --tb=no

The test loads the existing dedicated credential file privately; do not place its
contents on the command line. Do not use rerun plugins or repeat after failure.
Evidence is stored under a unique evidence/ddslab-semgrep-derived-* directory.
One new Product/Engagement, one import and one same-Test reimport; no cleanup.
Initial closure=false, reimport closure=true, product-wide closure=false; explicit
sync processing, external push disabled, engagement-scoped deduplication=true.
Global deduplication must already be false; no setting is changed.

Preflight compares pinned source/tag and configured image digests/image IDs,
runtime parser/importer/hash source, integration user privileges and scope,
API Product Type readiness, matching/hash/global deduplication configuration,
and parser output. No unsupported configuration is bypassed.

## Complete readbacks

Runtime DRF configuration was inspected read-only: LimitOffsetPagination builds
absolute next links from the request URL, retaining filters and adding limit/offset.
lab/finding_pages.py validates the absolute link against the exact original
scheme/host/port, findings path and test/limit/offset/ordering query. It never
requests a supplied URL; it constructs local requests. Redirects are disabled.
Unexpected protocol/host/path/userinfo/query, duplicate IDs, wrong ownership,
repeated cursor, missing count, count drift, empty continuation, truncated final
page, timeout or page exhaustion are INCONCLUSIVE. Limit: 20 pages by default,
configurable only between 1 and 100. No active/mitigated filters are used.
Per-page status, offset, count, row IDs and continuation presence are saved;
complete normalized per-finding evidence is saved after successful aggregation.
No arbitrary next URL or exception message is saved.

The new dedicated scenario uses this collector at both stages. Existing small
synthetic scenario tests remain unchanged; do not use their old single-page fetch
for large reports.

## Exact oracle

Pinned parser checks: 143/142 findings; every raw UID is the same placeholder;
all effective UIDs and services null; 143 distinct initial hashes and 142 unchanged
retained hash/rule pairs. No new logical identity and exactly one absent hash.
Initial readback must contain 143 active, unmitigated, nonduplicate findings with
exact parser hash/rule mapping. Reimport must retain the exact database ID set,
hash/rule association and Test ownership. Only the absent hash is inactive and
mitigated; all others stay active/unmitigated/nonduplicate. Persisted UIDs are
captured independently. Completion must explicitly be sync and complete.
Assertion discrepancies after mutations are FAIL, incomplete readback/processing
or transport failures INCONCLUSIVE. Neither classification alleges a vulnerability.

Offline tests exercise 100+43 pagination, negative pages/cursors/counts/hosts,
redirects, timeouts, ownership, lifecycle mass closure/replacement/removal, missing
or duplicate records, asynchronous completion and evidence token redaction.
Parser-only execution passed against the runtime without saving findings.
Live HTTP contract and end-to-end lifecycle remain unverified until separately
approved execution. Stop and inspect state read-only after any possible mutation.
