# M1-C preparation (live execution blocked)

The original M1-C gate rejected runtime always=[service]. The runtime read-only
probe confirmed hash_code, hash_fields=null, custom_hash_override=false and a
ready database. No API mutation or live scenario was attempted.

The prepared lab-only correction uses the existing invariant-service helper:
only [] or [service], absent/null services, no configured hash override or custom
method, three findings, A severity-only mutation, and zero changed hashes.
M1-A and M1-B checks are unchanged. Separate approval is required before execution.

Fixture A changes Low to Critical; B and C are unchanged. All effective services
are null. Calculated initial/reimport hashes are identical for A, B and C.
Pinned dojo/finding/models.py:929-932 and :1068-1077 establish that legacy hashing
excludes severity and appends only truthy always-included fields. This supports
identity preservation, not a claim about persisted severity reconciliation.
Reimport status routing is in dojo/importers/default_reimporter.py:1090-1112;
matched active handling begins at :1262. No live severity reconciliation has
been observed. Further reconciliation-path verification remains part of live
experiment preparation; do not assert overwrite or preservation from hashing.

Offline validation: 103 passed, 9 deselected; pytest, Ruff, compileall and
 git diff --check each exited 0. Thirteen targeted tests cover accepted field
lists, unsupported configurations, service drift, control changes and missing
severity mutation. No credentials, settings or records were changed.
