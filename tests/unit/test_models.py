from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lab import (
    EnvironmentType,
    ErrorClassification,
    EvidenceManifest,
    LabConfig,
    ResultStatus,
    ScenarioDefinition,
    VersionProvenance,
)
from lab import (
    TestResult as ResultModel,
)


def version() -> VersionProvenance:
    return VersionProvenance(application="3.5.101", verification_status="unverified")


def result(status: ResultStatus = ResultStatus.PASS, error=ErrorClassification.NONE) -> ResultModel:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return ResultModel(
        scenario_id="offline.fixture",
        status=status,
        version=version(),
        environment=EnvironmentType.OFFLINE,
        started_at=start,
        ended_at=start,
        expected_invariants=["same input has same checksum"],
        observed_outcomes={"count": 1},
        error_classification=error,
    )


def test_configuration_requires_version_metadata():
    config = LabConfig(
        project="lab",
        compose_project="ddslab",
        minikube_profile="ddslab",
        namespace="ddslab",
        versions={"baseline": version()},
    )
    assert config.versions["baseline"].application == "3.5.101"


def test_invalid_version_is_rejected():
    with pytest.raises(ValidationError):
        VersionProvenance(application="", verification_status="unverified")


def test_scenario_requires_invariant():
    with pytest.raises(ValidationError):
        ScenarioDefinition(scenario_id="bad", title="Bad", category="x")


def test_duplicate_scenario_fixture_ids_are_rejected():
    with pytest.raises(ValidationError):
        ScenarioDefinition(
            scenario_id="bad",
            title="Bad",
            category="x",
            expected_invariants=["one"],
            fixture_ids=["same", "same"],
        )


def test_pass_cannot_have_error_classification():
    with pytest.raises(ValidationError):
        result(ResultStatus.PASS, ErrorClassification.SETUP_FAILURE)


def test_fail_requires_error_classification():
    with pytest.raises(ValidationError):
        result(ResultStatus.FAIL, ErrorClassification.NONE)


def test_unsupported_is_skip_not_pass():
    observed = result(ResultStatus.SKIP, ErrorClassification.UNSUPPORTED_FEATURE)
    assert observed.status is ResultStatus.SKIP
    assert observed.status is not ResultStatus.PASS


def test_evidence_manifest_serializes_deterministically():
    manifest = EvidenceManifest(
        run_id="run-1",
        scenario_id="offline.fixture",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        result=result(),
        fixture_checksums={"fixture.json": "abc"},
    )
    assert manifest.canonical_json() == manifest.canonical_json()
    assert '"run_id": "run-1"' in manifest.canonical_json()


def test_missing_version_metadata_is_allowed_but_explicit():
    observed = result()
    assert observed.version is not None
    assert observed.version.source_sha is None
    assert observed.version.verification_status == "unverified"


def test_unsafe_evidence_path_is_rejected():
    payload = result().model_dump()
    payload["evidence_paths"] = ["../escape"]
    with pytest.raises(ValidationError):
        ResultModel(**payload)


def test_naive_timestamp_is_rejected():
    payload = result().model_dump()
    payload["started_at"] = datetime(2026, 1, 1)
    with pytest.raises(ValidationError):
        ResultModel(**payload)
