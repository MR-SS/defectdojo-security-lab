# M1-A service hash gate correction

This note supersedes the empty-always-fields requirement for M1-A only in
identity-mutations.md. No application configuration was changed.

Pinned DefectDojo 3.5.101 source:
- dojo/finding/models.py:929-932 constructs the legacy input from title, CWE,
  line, file_path and description.
- dojo/finding/models.py:1068-1077 appends each always-included field only when
  its value is truthy, then casefolds, UTF-8 encodes, strips the entire byte
  sequence and computes SHA-256. No field separator is inserted.
- dojo/importers/options.py:550-561 defaults omitted request service to None.
- dojo/importers/default_importer.py:257-258 and
  dojo/importers/default_reimporter.py:401-402 override report service only
  when request service is not None. An explicit empty request service therefore
  overrides report service with empty, whereas None leaves report service alone.

For the Finding model, omitted service and explicit null resolve to None; null
and empty string append nothing. A nonempty service appends its text; final
casefold/strip can make distinct strings hash-equivalent. Hash equivalence is
not service-scope equivalence: closure filters compare service separately.

The runner sends no request service and both fixtures omit service, so every
initial and reimport effective service is None. The gate deliberately allows
only absent/null fixture service, rejecting empty/explicit values even if their
hash suffix might be equivalent, to preserve the prepared closure scope.

Read-only runtime verification returned hash_code, no Generic hash-fields
configuration, always=[service], no custom hash override. Instantiating unsaved
Finding objects and calling compute_hash_code_legacy (no saves/imports) produced
exact parity with the local hash calculation for all six records. Only A's hash
changed; B/C remained stable. No database records were created or modified.

The gate accepts only always=[] or [service], absent/empty legacy field override,
explicitly false custom-method detection, three findings, identical null services,
and a file_path-only difference in A. It computes the hash delta and requires
exactly index 0 to change. Unknown/duplicate always fields, UID matching, custom
methods, configured hash-field overrides and service drift fail closed.

M1-B/C retain their existing stricter gates. M1-A remains conditional on these
invariants and runtime/source/image verification during a fresh approved run.
This correction is not an import test and does not establish live M1-A success.
