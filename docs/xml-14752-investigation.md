# Milestone 6A — bounded XML import investigation

## Decision and upstream status

Baseline lab commit 895abfeaca9dbcf3f198fbab0fadee536f63f3a6; target 3.5.101,
source 32aea6841a019b050737c8874b939b236095333e. Issue #14752 is open with one comment. Linked PR #14794
is closed, unmerged, closed as stale after conflicts. Maintainer asked why
catch at API rather than parser/importer level. Referenced commit 8f18e3e60bbb6b8d9aafdc67d80a086adf462177
changes serializer error handling; it is not evidence of a merged fix. A bounded
all-state search for 14752 returned only that issue and PR. XML ParseError PR
search additionally returned #4028 (dependency update) and #2604 (merged Nexpose
mapping fix). #9840 is merged and proposed lxml migration, but actual pinned
Burp/Dastardly source still imports defusedxml. Actual source wins over PR title.

The issue's claimed worker termination is NOT REPRODUCED. Its example uses Trivy
Scan, which is JSON in the pinned parser, not XML. The reported original XML
scan type is unspecified. We selected Burp Dastardly as a concrete small XML
path, not a claim to reproduce the reporter's deployment or historical 2.55.4.

Strongest candidate: confirmed shared XML ParseError-to-validation gap, already
reported as #14752. No new security vulnerability established. Coordinate with
the existing contributor rather than open a duplicate. A narrowly scoped parser
structure-validation follow-up is worthwhile but novelty remains unproven.

## Source-backed surface and reachability

Line references are pinned 3.5.101:
- dojo/api_v2/views.py:363-425: authenticated multipart ImportScanView and
  UserHasImportPermission, serializer.save. :481-519 reimport permissions and
  authorized Test queryset. No access-control bypass tested or identified.
- dojo/api_v2/serializers.py:584-620 and :878-943 invoke importer/reimporter;
  catch SyntaxError and ValueError by rethrowing generic Exception. This does
  not normalize ElementTree ParseError. Serializer validation/context creation
  precedes this; our seam probe does not execute that complete API path.
- dojo/importers/base_importer.py:375-395 invokes parser and converts only
  ValueError to Django ValidationError. :420-430 has the analogous dynamic
  parser seam. Our reproduction uses only the static seam.
- dojo/tools/burp_dastardly/parser.py:23-25 uses defusedxml.ElementTree.parse
  with XMLParser(); :29-37 assumes direct testsuite children, failures integer,
  name, testcase/failure message and type. No root/schema check. Whole XML tree
  is parsed before Finding construction. Missing attributes raise KeyError;
  unknown wrapper is silently ignored. No explicit application depth limit.
- dojo/tools/burp/parser.py:93-100 uses the same XML library/configuration;
  :170-176 indexes required child lists and assumes location text. Burp is a
  source-inspected sibling, not an executed second parser.
- dojo/tools/trivy/parser.py:get_findings uses json.loads. XML input there is
  not an ElementTree reproduction.
- dojo/api_v2/exception_handler.py:132-155 handles DRF/Django validation;
  :207-222 produces generic 500 for unrecognized exceptions. Optional
  api_expose_error_details changes message exposure; we mock it false, not
  modify settings. Handler is an API response boundary, not process termination.
- default_importer.py:118-126 parses before processing findings/closure, but
  :488-504 creates Test before parsing. Therefore 'parser is unsaved' does not
  prove the entire import has no prior writes. default_reimporter.py:121 parses
  before subsequent processing. Auto-create serializer path :904-915 can create
  context before invoking import. No whole-import transaction decorator was
  found in the inspected views/default importer/reimporter; rollback and actual
  residual records remain INCONCLUSIVE, not established corruption.
- base_importer.py:239-300 documents sync/async/async_wait post-processing
  dispatch/wait; default_importer.py:120 performs parsing first. Execution mode
  is not proof that parsing runs on a worker. No asynchronous paths executed.
- unittests/tools/test_burp_dastardly_parser.py:9-14 checks four findings from
  many_findings.xml; it does not cover malformed XML or missing attributes.

Scope is the selected Dastardly path and shared boundaries, not an exhaustive
inventory of every XML parser in DefectDojo. Other libraries/configurations
cannot inherit the entity-handling conclusions below.

## Experiment safety and method

Run `PYTHONPATH=. .venv/bin/python tests/xml_parser_probe.py` from lab root.
Existing container used solely for Python dependencies and exact source; no
HTTP requests, importer process_scan, saves or worker calls. Runtime Dastardly,
base_importer and exception_handler files matched pinned source byte-for-byte.

Nine synthetic fixtures are at fixtures/xml-14752/. Each <=2048 bytes, shallow
structure (at most testsuites/testsuite/testcase/failure); no external identifiers,
SYSTEM/PUBLIC entities or network payloads. Entity is one literal harmless value,
not expansion amplification. Probe bounds: 20-second process alarm, 35-second
caller timeout, 1 GiB address-space limit. It blocks database SQL and socket
connect/address lookup during cases. Fixtures contain no file-resource references.

First call the actual parser, counting unsaved Finding construction. Then call
the real BaseImporter static parse method on a simple seam with unsaved Test and
identity finalizer, and pass exceptions to the real custom_exception_handler.
System_Settings lookup, announcement and server-error logging are mocked to
avoid DB reads and unrelated effects. Returned status is a handler unit result,
NOT an HTTP request result. No persistence or transaction behavior is simulated.

Measured library: defusedxml 0.7.1, forbid_dtd=False, forbid_entities=True,
forbid_external=True. Declaring an internal entity is rejected. No XXE/SSRF,
external resource access, entity expansion or exhaustion demonstrated. DTD
permission alone does not imply entity permission. Unicode decoding is delegated
to XML parsing; an unknown encoding label was tested, not every invalid byte or
Unicode variant. No deep nesting/resource-limit claim is made from shallow tests.

## Actual outcomes and classification

Full exact messages, checksums and configuration: docs/xml-14752-results.json.
Expected validation for malformed input is 400, consistent with issue request
and existing ValueError conversion. No actual HTTP status was measured.

| Case | Parser outcome | Constructed / returned | Seam + handler | Classification |
|---|---|---|---|---|
| baseline | One synthetic finding | 1 / 1 | returns 1 | NOT REPRODUCED (successful control) |
| empty | ParseError: no element found | 0 / no return | ParseError, 500 | CONFIRMED DEFECT: rejection not normalized |
| truncated | ParseError: unclosed token | 0 / no return | ParseError, 500 | CONFIRMED DEFECT: same #14752 mechanism |
| encoding | LookupError: unknown encoding | 0 / no return | LookupError, 500 | CONFIRMED DEFECT: input-error normalization gap |
| entity | EntitiesForbidden | 0 / no return | ValidationError, 400 | EXPECTED REJECTION |
| invalid-integer | ValueError converting failures | 0 / no return | ValidationError, 400 | EXPECTED REJECTION |
| missing-attribute | KeyError: failures | 0 / no return | KeyError, 500 | CONFIRMED DEFECT: structural validation gap |
| partial | KeyError in second suite | 1 / no return | KeyError, 500 | CONFIRMED DEFECT: same gap; no partial returned list |
| unexpected-root | Empty list | 0 / 0 | returns 0 | INCONCLUSIVE semantic acceptance; no API success measured |

All constructed objects remained unsaved. 'Partial' means an object existed only
in a local list before exception, not a persisted finding or returned partial
result. Successful control is NOT REPRODUCED for the defect oracle. Unexpected
root accepting [] is measured; whether generic JUnit wrappers are supported and
whether this yields misleading successful imports needs a format-contract test.
An invalid empty-result input could reach closure processing in a full import;
that is a source-backed concern, not observed lifecycle damage.

## Impact and novelty

Availability: only per-input errors demonstrated. Probe completed all cases in
one process twice. This does not prove production resilience but contradicts
assuming every Python exception necessarily terminates a worker. No worker crash,
restart, persistent outage or resource exhaustion observed/tested.
Integrity: no database mutation; no returned partial findings on exceptions.
Pre-parse context/Test writes and rollback remain untested. Zero findings from
wrong-root input warrants caution, not a claim of mass closure.
Confidentiality: no unintended disclosure or external access demonstrated;
generic handler messages used with error-detail exposure disabled in mock.
Access control: authenticated permission gates exist; no boundary crossing tested.
Reliability: deterministic malformed-input exceptions map to server-error status
at the handler unit boundary rather than validation. Not a valid-report parsing
failure; severity is functional input-validation quality, not an established
security severity/CVE candidate.

ParseError is already reported. Missing failures and unsupported encoding differ
in exception class but overlap the same invalid-input reliability problem.
Bounded Dastardly issue search found #13467 and #9840, not an exact structural
validation report; this is not proof of novelty. No claim of a genuinely new
security finding. Current issue comment already proposes importer-level handling.

## Smallest proposed fix and regression

For #14752: catch ElementTree ParseError at the shared parser boundary alongside
existing ValueError, translate to sanitized Django ValidationError; cover both
static and dynamic parser seams where relevant. Do not blanket-catch Exception,
KeyError or LookupError globally: that hides implementation bugs. lxml XMLSyntaxError
is a separate library contract and needs a separate real-parser test before adding.

For Dastardly: validate recognized root, suite attributes and failure attributes
before constructing findings; raise ValueError with concise structural context.
Handle unsupported encoding narrowly around XML parsing if its exception contract
is confirmed for other supported encodings. Preserve valid zero-finding reports.

Regression tests should invoke real parser with truncated.xml through shared
parse seam, assert ValidationError then handler 400; valid baseline remains one.
Add invalid-integer and entity controls to prove existing safe rejection unchanged.
For structure validation compare legitimate empty testsuites versus wrong root,
missing failures and valid-first/invalid-second suites; ensure no result returned
on failure. Existing lab unit test verifies saved evidence/fixture integrity only,
not that an upstream fix exists or passes. Application source was not modified.

Next milestone: coordinate a narrow importer validation patch/test with #14752's
current contributor, then separately consider Dastardly structural validation.
No new general-purpose fuzzer. If persisted impact or real HTTP behavior is needed,
request separate approval for one isolated sync scenario with complete readback;
no such execution authorized or performed here. Worker/crash hypotheses require
additional separately scoped evidence, not repeated malformed live requests.

## Validation

Parser/seam probe completed twice, exit 0. Targeted evidence test: 1 passed,
exit 0. Offline pytest: 138 passed, 14 deselected, exit 0. Ruff, compilation
and git diff --check each exit 0. All nine fixture SHA-256 values are recorded
per case in xml-14752-results.json and checked by the offline test. These are
measured synthetic artifacts, not API traffic evidence.
