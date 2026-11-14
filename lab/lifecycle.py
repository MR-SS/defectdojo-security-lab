"""Offline contracts and opt-in runner for Generic Findings lifecycle tests."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .fixtures import generic_findings

INTEGRATION_OPT_IN_ENV = "DDSLAB_RUN_INTEGRATION"
FIXTURE_PATH = Path("fixtures/generic-findings-lifecycle-3.json")
REMOVAL_FIXTURE_PATH = Path("fixtures/generic-findings-removal-ac.json")


@dataclass(frozen=True)
class FindingState:
    """The API fields whose preservation is the lifecycle baseline contract."""

    finding_id: int
    unique_id_from_tool: str | None
    active: bool
    is_mitigated: bool


def load_lifecycle_fixture(path: Path = FIXTURE_PATH) -> bytes:
    content = path.read_bytes()
    payload = json.loads(content)
    findings = payload.get("findings")
    if not isinstance(findings, list) or len(findings) != 3:
        raise ValueError("lifecycle fixture must contain exactly three findings")
    for finding in findings:
        if not isinstance(finding, dict) or not all(
            isinstance(finding.get(field), str) and finding[field]
            for field in ("title", "description", "severity", "unique_id_from_tool")
        ):
            raise ValueError("lifecycle fixture has an invalid Generic Findings record")
    if content != generic_findings(3).content:
        raise ValueError("lifecycle fixture checksum does not match the approved baseline")
    return content


def load_removal_fixture(path: Path = REMOVAL_FIXTURE_PATH) -> bytes:
    """Load A/C fixture; its intentionally absent B models removal candidates."""
    content = path.read_bytes()
    payload = json.loads(content)
    findings = payload.get("findings")
    if not isinstance(findings, list) or len(findings) != 2:
        raise ValueError("removal fixture must contain exactly two findings")
    identities = {
        finding.get("unique_id_from_tool")
        for finding in findings
        if isinstance(finding, dict)
    }
    if identities != {"finding-0000", "finding-0002"}:
        raise ValueError("removal fixture must retain A/C identities and omit B")
    return content


def normalize_findings(response: dict[str, Any]) -> tuple[FindingState, ...]:
    results = response.get("results")
    if not isinstance(results, list):
        raise ValueError("finding list response lacks results")
    normalized: list[FindingState] = []
    for finding in results:
        try:
            normalized.append(
                FindingState(
                    finding_id=int(finding["id"]),
                    unique_id_from_tool=finding.get("unique_id_from_tool"),
                    active=bool(finding["active"]),
                    is_mitigated=bool(finding["is_mitigated"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("finding list response has ambiguous lifecycle fields") from error
    return tuple(sorted(normalized, key=lambda item: item.finding_id))


def assert_lifecycle_baseline(
    before: tuple[FindingState, ...], after: tuple[FindingState, ...]
) -> None:
    if len(before) != 3 or len(after) != 3:
        raise AssertionError("expected exactly three findings before and after reimport")
    if len({item.finding_id for item in after}) != 3:
        raise AssertionError("reimport created unexpected duplicate finding IDs")
    if before != after:
        raise AssertionError("identities or lifecycle fields changed on identical reimport")


def integration_is_enabled() -> bool:
    return os.getenv(INTEGRATION_OPT_IN_ENV) == "1"


def validate_contract_dry_run(path: Path = FIXTURE_PATH) -> dict[str, object]:
    """Validate tracked bytes and the invariant contract without network or database access."""
    content = load_lifecycle_fixture(path)
    payload = json.loads(content)
    return {
        "fixture_sha256": hashlib.sha256(content).hexdigest(),
        "finding_count": len(payload["findings"]),
        "import_fields": ("scan_type", "engagement", "file", "test_title"),
        "reimport_fields": ("scan_type", "test", "file"),
        "writes_performed": False,
    }


def get_findings_for_test(
    client: httpx.Client, headers: dict[str, str], test_id: int
) -> tuple[FindingState, ...]:
    response = client.get(
        "/api/v2/findings/", headers=headers, params={"test": test_id, "limit": 100}
    )
    if response.status_code != 200:
        raise RuntimeError(f"finding read returned HTTP {response.status_code}")
    return normalize_findings(response.json())
