# M1-B invariant-service hash gate

The M1-B gate now accepts always-included fields [] or [service] only with
hash_code matching, no configured hash-field override, explicitly absent custom
hash method, three findings, and absent/null effective service throughout.
The request continues to omit service. Unknown or duplicate always fields and
non-null or unequal fixture service are rejected.

Pinned 3.5.101 dojo/finding/models.py:929-932 hashes title, CWE, line, file_path
and description. Lines 1068-1077 append truthy always-included fields, then
casefold, encode, strip and SHA-256. UID is not among these inputs. Therefore
the M1-A service analysis applies without changing the matching algorithm.

Exact M1-B fixtures change only A.unique_id_from_tool from finding-0000 to
finding-mutated-0000. B/C are unchanged. Read-only runtime configuration probe
confirmed hash_code, hash_fields=null, always=[service], custom override=false.
The calculated initial and changed hash arrays were identical for all three
findings; effective services were all null.

A common internal validator preserves M1-A's file_path-only change and exactly
one changed hash, while M1-B requires UID-only change and zero changed hashes.
M1-C retains its prior stricter gate. The runner records M1-B hash invariants
before entering the API request path. Persisted UID reconciliation remains an
observation, not an assertion derived from hash equivalence.

Validation: 90 offline tests passed, 9 integration cases deselected; pytest,
Ruff, compilation and git diff --check each exited 0. New tests cover allowed
always-field lists, duplicate/unknown fields, overrides, non-hash matching,
missing custom-method confirmation, service drift, path drift, control UID
drift and a missing UID mutation. No scenario was executed or database record
changed. Live execution requires separate approval and fresh preflight.
