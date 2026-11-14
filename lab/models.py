"""Pydantic schemas and deterministic serialization for offline scenarios."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResultStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ErrorClassification(StrEnum):
    NONE = "none"
    ASSERTION_FAILURE = "assertion_failure"
    SETUP_FAILURE = "setup_failure"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    UNVERIFIED_BEHAVIOR = "unverified_behavior"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    INPUT_VALIDATION = "input_validation"


class EnvironmentType(StrEnum):
    OFFLINE = "offline"
    COMPOSE = "compose"
    MINIKUBE = "minikube"


class VersionProvenance(StrictModel):
    application: str = Field(min_length=1)
    source_ref: str | None = None
    source_sha: str | None = None
    image: str | None = None
    image_digest: str | None = None
    chart: str | None = None
    chart_version: str | None = None
    verification_status: str = "unverified"

    @field_validator("source_sha", "image_digest")
    @classmethod
    def nonempty_if_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("metadata must be null or non-empty")
        return value


class LabConfig(StrictModel):
    project: str = Field(min_length=1)
    local_only: bool = True
    require_loopback_bindings: bool = True
    compose_project: str = Field(min_length=1)
    minikube_profile: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    versions: dict[str, VersionProvenance] = Field(min_length=1)

    @field_validator("local_only", "require_loopback_bindings")
    @classmethod
    def security_controls_enabled(cls, value: bool) -> bool:
        if not value:
            raise ValueError("local-only security controls cannot be disabled")
        return value


class ScenarioDefinition(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    environment: EnvironmentType = EnvironmentType.OFFLINE
    supported_versions: list[str] = Field(default_factory=list)
    expected_invariants: list[str] = Field(min_length=1)
    fixture_ids: list[str] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("supported_versions", "fixture_ids")
    @classmethod
    def no_duplicates(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate identifiers are not allowed")
        return value


class TestResult(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    status: ResultStatus
    version: VersionProvenance | None = None
    environment: EnvironmentType
    started_at: datetime
    ended_at: datetime
    input_checksums: dict[str, str] = Field(default_factory=dict)
    expected_invariants: list[str] = Field(default_factory=list)
    observed_outcomes: dict[str, Any] = Field(default_factory=dict)
    evidence_paths: list[str] = Field(default_factory=list)
    error_classification: ErrorClassification = ErrorClassification.NONE
    error_message: str | None = None

    @field_validator("started_at", "ended_at")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None or offset.total_seconds() != 0:
            raise ValueError("timestamps must be timezone-aware UTC")
        return value.astimezone(UTC)

    @field_validator("ended_at")
    @classmethod
    def end_after_start(cls, value: datetime, info: Any) -> datetime:
        start = info.data.get("started_at")
        if start is not None and value < start:
            raise ValueError("ended_at must not precede started_at")
        return value

    @field_validator("evidence_paths")
    @classmethod
    def safe_paths(cls, value: list[str]) -> list[str]:
        for path in value:
            pure = PurePosixPath(path)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError("evidence paths must be relative and contained")
        return value

    @field_validator("error_classification")
    @classmethod
    def status_error_consistency(cls, value: ErrorClassification, info: Any) -> ErrorClassification:
        status = info.data.get("status")
        if status == ResultStatus.PASS and value != ErrorClassification.NONE:
            raise ValueError("PASS cannot carry an error classification")
        needs_classification = {
            ResultStatus.FAIL, ResultStatus.BLOCKED, ResultStatus.SKIP, ResultStatus.INCONCLUSIVE
        }
        if status in needs_classification and value == ErrorClassification.NONE:
            raise ValueError("non-PASS results require an error classification")
        return value


class EvidenceManifest(StrictModel):
    schema_version: int = 1
    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    created_at: datetime
    result: TestResult
    fixture_checksums: dict[str, str] = Field(default_factory=dict)
    generator_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def created_at_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must be UTC")
        return value.astimezone(UTC)

    def canonical_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=True)
