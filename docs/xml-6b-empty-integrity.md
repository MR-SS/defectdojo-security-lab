# Milestone 6B — Empty XML reimport and Finding integrity

Starting commit: 89afe9d9096c53bbb517d483c8b2faf09104fb70. Target DefectDojo 3.5.101, pinned source
32aea6841a019b050737c8874b939b236095333e. This investigation is independent of malformed XML issue #14752.
No imports, reimports, database writes, API requests, worker execution, cleanup or
application changes were performed.

## Source-backed control flow

`BurpDastardlyParser.get_findings` parses with `defusedxml.ElementTree.parse`,
then `get_items` searches only direct `testsuite` children. Both `<testsuites/>`
and `<unexpected/>` are well-formed and return an empty list. The parser has no
root/schema validation and does not distinguish valid-empty from unsupported-root
input.

DefaultImporter and DefaultReImporter both parse first, process `parsed_findings
or []`, then invoke close-old behavior when enabled. No source-level empty-result
guard was found. DefaultImporter closure filters active/risk-accepted findings,
matching Test_Type, excludes the current Test, removes incoming hash/UID matches,
then applies product or engagement scope and exact request-level service. An
omitted request service selects only null/empty-service findings. Reimport keeps
same-Test bookkeeping, while its closure behavior operates on that reimport set.

Parsing occurs before finding processing, but import code can create a Test before
parsing. The inspected paths do not establish an all-operation transaction
boundary. These facts make persisted rollback behavior unverified, not corrupted.
The API does not distinguish valid-empty and unexpected-root Dastardly XML.

Relevant pinned source:

- `dojo/tools/burp_dastardly/parser.py:23-37`
- `dojo/importers/base_importer.py:375-395`
- `dojo/importers/default_importer.py:118-126, 400-420`
- `dojo/importers/default_reimporter.py:121-130, 869-900`
- `dojo/api_v2/views.py:363-425, 481-519`
- `dojo/api_v2/serializers.py:584-620, 878-943`

## Offline reproduction

Fixtures:

- `fixtures/xml-6b/baseline.xml`: three distinct findings.
- `fixtures/xml-6b/valid-empty.xml`: well-formed `<testsuites/>`.
- `fixtures/xml-6b/unexpected-root.xml`: well-formed unsupported root.
- `fixtures/xml-6b/malformed.xml`: truncated XML.

Observed parser results:

  baseline         success, 3 findings
  valid-empty      success, 0 findings
  unexpected-root  success, 0 findings
  malformed        ParseError, no findings

The exact parser output and SHA-256 values are in:

`docs/xml-6b-results.json`

`tests/xml_empty_probe.py` calls only the real parser with unsaved Test objects.
Inputs are under 4096 bytes, shallow, local-only and contain no external payloads.

A separate source-level unit model verifies closure selection for same-Test,
engagement and product scopes, plus omitted request-service behavior. It does not
pretend to execute a database lifecycle.

## Reachability assessment

The suspected sequence is source-reachable only when all conditions hold:

1. An authorized importer submits well-formed XML accepted by the Dastardly
   parser but containing no direct `testsuite` findings.
2. `close_old_findings=true` is enabled.
3. The importer/scope includes the existing findings.
4. Existing findings meet active/risk-accepted, Test_Type and service filters.
5. For nonempty services, the request-level service matches exactly.
6. No validation guard rejects the empty result.

The parser experiment confirms conditions 1 and 6 for the selected fixtures. It
does not confirm a persisted lifecycle transition. Therefore unintended closure
is INCONCLUSIVE as an observed product defect.

A truly empty report may legitimately close findings if the scanner contract
means a completed scan with no findings. An unsupported root silently producing
zero findings is different and creates contract ambiguity. A closure after that
input would represent a security-reporting integrity risk, but no such closure
was observed here.

An omitted request-level service normally prevents closure of parser findings
with nonempty service. A live test would need explicit stable service, synchronous
processing, complete before/after readbacks and separate valid-empty/unexpected-root
expectations.

## Impact and existing coverage

Confirmed:

- Unexpected well-formed XML is accepted as a successful zero-finding parse.
- Valid-empty XML is also accepted as zero findings.
- No protective empty-result or root validation guard exists in the inspected path.

Not demonstrated:

- Finding mitigation or inactivity.
- Database corruption or partial persistence.
- Worker crash or service disruption.
- Confidentiality impact, SSRF, XXE or access-control bypass.
- Incorrect closure in a live API scenario.

Issue #14752 covers malformed XML exception handling. It does not cover this
well-formed empty/unsupported-root ambiguity. No existing fix adding Dastardly
root validation was identified.

## Controlled experiment decision

A live experiment is justified only after separate approval. It should use one
isolated same-Test scenario with three initial findings, explicit
`close_old_findings=true`, stable request service, synchronous processing, full
active/inactive/mitigated readbacks, no retries and no cleanup. The valid-empty
case may legitimately close findings; the unexpected-root case should be judged
against the agreed parser contract. Malformed XML remains outside this experiment.

## Recommendation

CONTINUE with one approval-gated lifecycle experiment, not a security report.
Ask maintainers whether `<testsuites/>` is a valid completed empty report. If the
format requires a recognized root, add a narrow root/schema validation guard
before close-old processing. Do not add a blanket zero-findings rejection until
that contract is established.

## Validation

Targeted offline tests: 3 passed, exit 0. Full offline pytest: 140 passed,
14 integration tests deselected, exit 0. Ruff, Python compilation and
git diff --check each exited 0. The parser probe completed with exit 0. No live
integration test was run, so no lifecycle transition is claimed.
