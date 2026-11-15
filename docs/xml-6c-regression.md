# Milestone 6C — XML Reimport Integrity Regression

Status: prepared only. No live imports, reimports, database writes, worker execution, cleanup or infrastructure changes were performed.

## Format contract

The pinned Burp Dastardly parser uses `defusedxml.ElementTree.parse` and iterates direct `testsuite` children. The tracked parser-only probe establishes:

- `fixtures/xml-6b/valid-empty.xml` (`<testsuites/>`) is well-formed and returns zero findings.
- `fixtures/xml-6b/unexpected-root.xml` (`<unexpected/>`) is well-formed and also returns zero findings, but does not match the expected report structure.
- `fixtures/xml-6b/malformed.xml` raises `ParseError`.
- `fixtures/xml-6b/baseline.xml` returns three findings.

`<testsuites/>` is therefore parser-accepted as an empty result, but the repository does not establish a documented product contract that an empty report should close findings. `<unexpected/>` is an unsupported-root candidate, not a valid empty report. No alternative root was introduced by this milestone; the parser's inspected behavior only recognizes direct `testsuite` children.

## Closure preconditions

The prepared lifecycle oracle requires all of the following:

- same Test for the reimport;
- explicit `close_old_findings=true`;
- product-wide closure disabled;
- matching Test Type;
- explicit stable request service `xml-6c-stable-service`;
- three initially active findings and complete before/after reads, including inactive records;
- synchronous completion;
- deterministic fixture bytes and parser/source/image correspondence;
- no retry and no cleanup.

The request-level service is explicit because it can override parser-generated service. This prevents the experiment from conflating service filtering with parser identity. Existing source inspection remains the basis for the exact DefaultImporter, DefaultReImporter, serializer and closure-selection references recorded in `docs/xml-6b-empty-integrity.md`.

## Separate scenarios

`tests/integration/test_xml_6c.py` defines two distinct approval domains:

- `XML-EMPTY-CONTROL`: baseline followed by same-Test reimport of `valid-empty.xml`. Expected result is contract-dependent: legitimate empty-scan behavior may mitigate eligible findings, while a protective validation guard would reject it without mutation.
- `XML-INVALID-ROOT`: a separate Product/Engagement/Test context followed by `unexpected-root.xml`. Expected result is validation rejection without lifecycle mutation. If accepted, the oracle must record whether findings are mitigated and whether the API reports misleading success.

Both entrypoints are deliberately non-executing in this milestone. Each requires `DDSLAB_RUN_INTEGRATION=1` and its own exact `DDSLAB_APPROVE_SCENARIO` value; approvals cannot be shared. No credentials are embedded in tracked files.

## Fixture checksums

- `baseline.xml`: `c9c7d6474447d2ac91637bed36b649306606858119d3655818ba385175faf202`
- `valid-empty.xml`: `ccacac3cd5303b2f3c2bb26ee0838b3aa409173a473fd700062b1cd787d5d1b8`
- `unexpected-root.xml`: `a8c11b30f8edcd179d79ff4a399fff445a5681ef58c66dcfb95998ae056395c6`
- `malformed.xml`: `f9d13198ad5b30db7b4ced387e376e193a08a343127d8b052a4a874b18b36c0b`

## Decision

The candidate merits continued investigation only through two separately approved live runs. Do not classify it as a security vulnerability from parser-only evidence. The key decision is whether the product intentionally treats a recognized empty report as a completed zero-finding scan. An unsupported root should be rejected or clearly classified before any close-old operation; acceptance with mitigation would establish an integrity/reliability defect, not unauthorized access.
