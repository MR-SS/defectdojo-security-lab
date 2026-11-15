# Upstream Proposal: Burp Dastardly Root-Element Validation (6H)

## Root cause

`BurpDastardlyParser.get_findings` (dojo/tools/burp_dastardly/parser.py at
32aea6841a019b050737c8874b939b236095333e) parses any well-formed XML and then iterates
`tree.findall("testsuite")`. For a document whose root is not the JUnit-style
`testsuites`/`testsuite` (e.g. `<unexpected/>`), the findall yields nothing and
the parser returns `[]` — an empty finding list that the importer treats as a
completed empty scan. With `close_old_findings=true`, a same-Test reimport of
such an out-of-contract document mitigates ALL previously active findings.

## Demonstrated impact (evidence-backed, 2026-11-15)

- Control (`XML-EMPTY-CONTROL`, Test 13): legitimate `<testsuites/>` empty
  report, reimport HTTP 201, findings 174-176 all mitigated — CORRECT product
  behavior for a completed empty scan.
- Defect (`XML-INVALID-ROOT`, Test 14): `<unexpected/>` root, reimport
  HTTP 201 ("0 findings parsed"), findings 177-179 all mitigated in the same
  way — INCORRECT, because the document is not a Dastardly report at all.
  Verdict recorded by the oracle: `integrity-defect-exhibited`
  (created 0 / closed 3 / unchanged 0 / reactivated 0).

Both runs: isolated Product/Engagement under Product Type 3, explicit request
service `xml-6c-stable-service`, `close_old_findings_product_scope=false`,
synchronous processing, complete before/after readbacks. Evidence:
`evidence/xml-empty-control-ffd6e9d0d72f/`, `evidence/xml-invalid-root-986644219c83/`.

Classification: Data Integrity defect. NOT a security vulnerability on current
evidence — it requires an authorized importer, stays within the authorized
Product/Test boundary, and audit history is preserved.

## Proposed fix (minimal)

Validate the document root in `get_findings` before `get_items`:

- Accept roots `testsuites` and `testsuite` (namespace-insensitive via
  `tag.rpartition("}")[2]`, matching how other DefectDojo JUnit-family parsers
  handle namespaced documents).
- Otherwise raise `ValueError("Unexpected root element ...")`.

`ValueError` is the existing convention: `base_importer.parse_findings_static_test_type`
converts it to a DRF `ValidationError` (HTTP 400), exactly like every other
"this is not a valid report for this parser" rejection. No other behavior
changes; `ParseError` for malformed XML is untouched.

Patch: `upstream-proposals/0001-burp-dastardly-root-validation.patch`
(regenerable via `upstream-proposals/generate_patch.py` from the pinned source).

## Container validation of the patch

Applied to a copy of the pinned parser and exec'd inside the running
ddslab-uwsgi-1 container (stdin-only, nothing written):

  case           result
  baseline.xml   ok, 3 findings
  valid-empty    ok, 0 findings   (legitimate empty report preserved)
  bare <testsuite> root  ok, 0 findings (historical export shape preserved)
  <unexpected/>  ValueError       (rejected before closure logic)
  malformed.xml  ParseError       (unrelated parse errors untouched)

## Proposed upstream regression tests

1. Parser unit test (unittests/tools/test_burp_dastardly_parser.py):
   - `<testsuites/>` empty document -> `[]` (no exception).
   - `<unexpected/>` document -> `pytest.raises(ValueError)`.
2. API integration test (unittests/api_v2/...): create Test with 3 active
   findings; reimport `<unexpected/>` with `close_old_findings=true`; assert
   HTTP 400 and all three findings still active/not mitigated.

## Issue/PR overlap

- Issue #14752 (open at investigation time): malformed-XML `ParseError`
  reaching a generic 500 — related boundary, different failure mode (this
  proposal is about well-formed but out-of-contract documents returning
  success). Complementary, not duplicate.
- PR #14794 (closed/unmerged/stale at investigation time): unrelated
  error-handling change; no root-validation overlap found.
- No open PR adds root validation to burp_dastardly as of the pinned source.

## Backward compatibility

- Real Dastardly exports use the `<testsuites>` root (upstream fixture
  `many_findings.xml` confirms); a bare `<testsuite>` root remains accepted.
- Namespaced JUnit documents remain accepted (namespace stripped before check).
- Documents previously "imported" as silent empty scans will now 400. Any
  workflow relying on uploading arbitrary well-formed XML to close findings
  breaks — that reliance is precisely the defect.
- Legitimate empty scans (`<testsuites/>` with zero testsuites) keep closing
  findings under close_old_findings=true, as demonstrated by the control run.

## Submission recommendation

File a single upstream issue with: root cause, both evidence runs (control vs
defect), the minimal patch, and the two regression tests. Suggested title:
"burp_dastardly: well-formed XML with unexpected root accepted as empty scan,
mitigating all findings on reimport". Not security-advisory material.
