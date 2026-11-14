# Milestone 3C: reproducibility and identity mutation

## Preserved executed baseline

R1/I1 evidence was inspected offline: 78 JSON documents parsed, both summaries PASS,
and both original fixture checksums match tracked generator bytes. A recursive
sensitive-key audit (password, authorization, cookie, secret, token, API key) found
no populated sensitive fields. This is not proof against arbitrary secrets embedded
in free text. No credentials were read for this audit; no runtime calls were made.
Raw evidence remains untracked and is not included in the commit.

The temporary execution script had materially stronger checks than the old pytest
entrypoints: DB readiness, algorithm checks, isolation reads, readbacks, explicit
request flags, completion checks and persisted responses. `lab/experiment_runner.py`
preserves these in a shared runner. It deliberately uses an externally supplied
API token rather than extracting administrator credentials from container settings.
It records images, effective configuration, fixture bytes/checksums, intents before
requests, responses, ownership and before/after states. Failure never retries a POST
or deletes records. Evidence is exclusive-create, nested secret keys are redacted,
and the supplied token is removed even from free text. Response headers/cookies are
not collected. Existing old integration entrypoints remain historical; use the new
single shared entrypoint for reproducible experiments.

R1 and I1 each use a fresh Product/Engagement, engagement deduplication enabled,
service unset, Info threshold, sync processing and product closure scope false.
Initial import explicitly sets close_old_findings=false. The second request sets
it true; reimport also sets do_not_reactivate=false. Test IDs are response-derived.
The runner preserves separate Test ownership in I1; duplicate marking is recorded
separately from identity matching. No automatic cleanup exists.

## Source-derived identity behavior

Pinned tag 3.5.101: `dojo/settings/settings.dist.py:1838` selects hash_code for
Generic Findings Import. `dojo/importers/default_reimporter.py:1038-1046` uses
only the hash in hash mode and only UID in UID mode. The combined branch at
1048-1078 accepts either. UID presence does not switch algorithms.

`dojo/finding/models.py:861-927` permits configured fields or a custom hash method.
With no configured fields it falls back to `compute_hash_code_legacy` at 929-932:
title + CWE + line + file_path + description, then hash_fields. Thus UID and severity
are not legacy hash inputs. Service/always-included fields must remain controlled.
`default_reimporter.py:310-328,592-608,869-916` closes unmatched originals in the
same Test/service. Matched mitigated records use the separate reactivation path at
1150-1260; these experiments start active and unmitigated and must not exercise it.

The runner refuses non-hash algorithms and, for mutation cases, configured hash
fields/always fields rather than assuming its legacy-field oracle still applies.
A custom hash override or image/source mismatch must be ruled out during approved
preflight; no configuration changes are authorized by these tests.

## Controlled cases (only A changes; B/C are controls)

- M1-A: keep UID, change only A.file_path. Expected under legacy hash inputs:
  hash differs; original A is closed, new A is created active with a different ID
  and the same UID. Four rows remain (three active, one mitigated). This expected
  identity split can look like false closure but is not a defect under hash matching.
  A UID-keyed dictionary would hide a row; the runner stores rows by database ID.
- M1-B: change only A.unique_id_from_tool. Hash remains equal; expected same three
  database IDs and no closure/reactivation. Persisted UID reconciliation is captured
  as an observation, not assumed to update. Creating a fourth row despite an equal
  effective hash is a candidate discrepancy, not yet a demonstrated product bug.
- M1-C: change only A.severity from Low to Critical. With legacy hash inputs the
  same IDs should match and remain active/unmitigated. Severity reconciliation is
  captured independently; matching does not itself guarantee severity overwrite.
  A custom hash including severity would invalidate this experiment's oracle.

These are hash-mode tests, NOT tests of UID-mode matching. UID-mode expectations
would differ (M1-A match, M1-B split); exercising them requires separate approval
for an isolated configuration, not silently changing this application's settings.

All three require independent Product/Engagements and exactly one initial import
and one same-Test reimport. Unexpected closure of B/C, extra rows (except M1-A's
single expected new row), ownership changes, or reactivation are failures of the
oracle. Missing response/completion/configuration information is INCONCLUSIVE.
No defect claim is supported without a separately approved reproduction.

## Offline and approval-gated use

Deterministic synthetic mutation fixtures are generated by
`lab.experiments.fixture('M1-A'|'M1-B'|'M1-C')`; complete bytes and hashes are stored
with each approved run. The existing tracked ABC fixture is unchanged. Unit tests
verify exactly the intended field differs, repeated UIDs survive normalization,
unsafe/incomplete ownership responses are rejected, token redaction and opt-in.

Offline: `.venv/bin/pytest -m 'not integration'`

Only AFTER explicit approval, with DDSLAB_API_BASE_URL set to literal loopback,
DDSLAB_API_TOKEN supplied privately, and DDSLAB_PRODUCT_TYPE_ID selected:

Also set DDSLAB_SOURCE_CHECKOUT to the existing read-only 3.5.101 Git checkout;
the runner verifies HEAD equals the release tag and records the resolved commit.

    DDSLAB_RUN_INTEGRATION=1 DDSLAB_APPROVE_SCENARIO=M1-A \
      .venv/bin/pytest tests/integration/test_experiments.py -k M1-A

Select M1-B or M1-C independently, never a broad suite with multiple mutation flags.
R1/I1 can also use this entrypoint, but must not be repeated without fresh approval.
Current milestone performs no live experiment and does not establish mutation PASS.
