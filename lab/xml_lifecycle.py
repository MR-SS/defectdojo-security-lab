"""Approval-gated Burp Dastardly XML lifecycle runner."""
from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .lifecycle import FindingState

PINNED_SOURCE = "32aea6841a019b050737c8874b939b236095333e"
BASELINE = Path("fixtures/xml-6b/baseline.xml")
EMPTY = Path("fixtures/xml-6b/valid-empty.xml")
SCENARIO = "XML-EMPTY-CONTROL"
SERVICE = "xml-6c-stable-service"
EXPECTED_FIXTURES = {
    BASELINE: "c9c7d6474447d2ac91637bed36b649306606858119d3655818ba385175faf202",
    EMPTY: "ccacac3cd5303b2f3c2bb26ee0838b3aa409173a473fd700062b1cd787d5d1b8",
}
PARSER_FILES = (
    "dojo/tools/burp_dastardly/parser.py",
    "dojo/importers/default_importer.py",
    "dojo/importers/default_reimporter.py",
    "dojo/importers/base_importer.py",
    "dojo/api_v2/serializers.py",
)


@dataclass(frozen=True)
class RunResult:
    stage: str
    status: int


class GateBlocked(RuntimeError):
    """Raised before a mutating HTTP request is permitted."""


def fixture_hashes() -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in EXPECTED_FIXTURES}


def verify_fixtures() -> None:
    if fixture_hashes() != {str(path): digest for path, digest in EXPECTED_FIXTURES.items()}:
        raise GateBlocked("fixture checksum mismatch")
    if any(len(path.read_bytes()) > 4096 for path in EXPECTED_FIXTURES):
        raise GateBlocked("fixture exceeds bounded input size")


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, timeout=15, check=False
    )
    if result.returncode:
        raise GateBlocked("source git command failed")
    return result.stdout.strip()


def verify_source_checkout(path: Path) -> dict[str, Any]:
    if not path.is_dir() or not (path / ".git").exists():
        raise GateBlocked("DDSLAB_SOURCE_CHECKOUT is not a Git checkout")
    if _git(path, "rev-parse", "HEAD") != PINNED_SOURCE:
        raise GateBlocked("source checkout HEAD is not the pinned release")
    if _git(path, "rev-parse", "3.5.101^{commit}") != PINNED_SOURCE:
        raise GateBlocked("source checkout tag does not resolve to the pinned release")
    if _git(path, "status", "--porcelain"):
        raise GateBlocked("source checkout has uncommitted changes")
    hashes: dict[str, str] = {}
    for relative in PARSER_FILES:
        blob = subprocess.run(
            ["git", "-C", str(path), "show", f"HEAD:{relative}"],
            capture_output=True,
            timeout=15,
            check=False,
        )
        if blob.returncode:
            raise GateBlocked(f"missing pinned source file: {relative}")
        hashes[relative] = hashlib.sha256(blob.stdout).hexdigest()
    return {"commit": PINNED_SOURCE, "files": hashes}


def verify_runtime_correspondence(provenance: dict[str, Any]) -> None:
    for relative, expected in provenance["files"].items():
        result = subprocess.run(
            ["docker", "exec", "ddslab-uwsgi-1", "sha256sum", f"/app/{relative}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode or result.stdout.split(maxsplit=1)[0] != expected:
            raise GateBlocked(f"runtime source mismatch: {relative}")


def approval_enabled(env: dict[str, str]) -> bool:
    return env.get("DDSLAB_RUN_INTEGRATION") == "1" and env.get(
        "DDSLAB_APPROVE_SCENARIO"
    ) == SCENARIO


def require_gate(
    env: dict[str, str],
    source_verifier: Callable[[Path], dict[str, Any]] = verify_source_checkout,
    runtime_verifier: Callable[[dict[str, Any]], None] = verify_runtime_correspondence,
) -> dict[str, Any]:
    if not approval_enabled(env):
        raise GateBlocked("missing exact integration opt-in or scenario approval")
    source = env.get("DDSLAB_SOURCE_CHECKOUT")
    if not source:
        raise GateBlocked("DDSLAB_SOURCE_CHECKOUT is required")
    verify_fixtures()
    provenance = source_verifier(Path(source))
    runtime_verifier(provenance)
    if env.get("DDSLAB_PRODUCT_TYPE_ID") != "3":
        raise GateBlocked("Product Type 3 is required")
    if not env.get("DDSLAB_API_BASE_URL") or not env.get("DDSLAB_API_TOKEN"):
        raise GateBlocked("authenticated API configuration is incomplete")
    return provenance


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError as error:
        raise GateBlocked("API response was not JSON") from error
    if not isinstance(value, dict):
        raise GateBlocked("API response body was not an object")
    return value


def _sync_complete(payload: dict[str, Any]) -> bool:
    return payload.get("deduplication_complete") is True or payload.get("status") in {
        "complete", "completed", "success"
    }


def read_findings(
    client: httpx.Client, headers: dict[str, str], test_id: int
) -> tuple[FindingState, ...]:
    response = client.get(
        "/api/v2/findings/", headers=headers, params={"test": test_id, "limit": 100, "offset": 0}
    )
    if response.status_code != 200:
        raise GateBlocked(f"finding read returned HTTP {response.status_code}")
    payload = _json(response)
    results = payload.get("results")
    if not isinstance(results, list):
        raise GateBlocked("finding read lacked results")
    rows: list[FindingState] = []
    for row in results:
        try:
            rows.append(
                FindingState(
                    finding_id=int(row["id"]),
                    unique_id_from_tool=row.get("unique_id_from_tool"),
                    active=bool(row["active"]),
                    is_mitigated=bool(row["is_mitigated"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise GateBlocked("finding lifecycle fields were incomplete") from error
        if row.get("test") not in (None, test_id, str(test_id)):
            raise GateBlocked("finding ownership does not match target Test")
    if len(rows) != 3 or len({row.finding_id for row in rows}) != 3:
        raise GateBlocked("expected exactly three distinct Finding IDs")
    return tuple(sorted(rows, key=lambda row: row.finding_id))


def execute_empty_control(
    *,
    env: dict[str, str] | None = None,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
    source_verifier: Callable[[Path], dict[str, Any]] = verify_source_checkout,
    runtime_verifier: Callable[[dict[str, Any]], None] = verify_runtime_correspondence,
) -> dict[str, Any]:
    """Perform exactly one approved baseline import and one approved reimport."""
    values = dict(os.environ if env is None else env)
    provenance = require_gate(values, source_verifier, runtime_verifier)
    headers = {"Authorization": f"Token {values['DDSLAB_API_TOKEN']}"}
    run_id = f"xml-empty-control-{uuid.uuid4().hex[:12]}"
    statuses: list[RunResult] = []
    with client_factory(
        base_url=values["DDSLAB_API_BASE_URL"], headers=headers, timeout=60, trust_env=False
    ) as client:
        readiness = client.get("/api/v2/", headers=headers)
        if readiness.status_code != 200:
            raise GateBlocked(f"API readiness returned HTTP {readiness.status_code}")
        product_type = client.get("/api/v2/product_types/3/", headers=headers)
        if product_type.status_code != 200 or _json(product_type).get("id") != 3:
            raise GateBlocked("Product Type 3 isolation could not be verified")
        product = client.post(
            "/api/v2/products/",
            json={
                "name": run_id,
                "description": "Synthetic XML-6C scenario.",
                "prod_type": 3,
            },
        )
        if product.status_code != 201:
            raise GateBlocked(f"Product creation returned HTTP {product.status_code}")
        engagement = client.post(
            "/api/v2/engagements/",
            json={
                "name": run_id,
                "product": _json(product)["id"],
                "target_start": "2026-11-15",
                "target_end": "2026-11-16",
                "status": "In Progress",
                "engagement_type": "CI/CD",
            },
        )
        if engagement.status_code != 201:
            raise GateBlocked(f"Engagement creation returned HTTP {engagement.status_code}")
        engagement_id = _json(engagement)["id"]
        imported = client.post(
            "/api/v2/import-scan/",
            data={
                "scan_type": "Burp Dastardly Scan", "engagement": str(engagement_id),
                "minimum_severity": "Info", "deduplication_execution_mode": "sync",
                "test_title": run_id, "close_old_findings": "false", "service": SERVICE,
            },
            files={"file": ("baseline.xml", BASELINE.read_bytes(), "application/xml")},
        )
        statuses.append(RunResult("baseline_import", imported.status_code))
        imported_payload = _json(imported)
        if imported.status_code != 201 or not _sync_complete(imported_payload):
            raise GateBlocked("baseline import did not complete synchronously")
        test_id = int(imported_payload["test"])
        before = read_findings(client, headers, test_id)
        reimported = client.post(
            "/api/v2/reimport-scan/",
            data={
                "scan_type": "Burp Dastardly Scan", "test": str(test_id),
                "minimum_severity": "Info", "deduplication_execution_mode": "sync",
                "close_old_findings": "true", "close_old_findings_product_scope": "false",
                "do_not_reactivate": "false", "service": SERVICE,
            },
            files={"file": ("valid-empty.xml", EMPTY.read_bytes(), "application/xml")},
        )
        statuses.append(RunResult("empty_reimport", reimported.status_code))
        reimported_payload = _json(reimported)
        if reimported.status_code != 201 or not _sync_complete(reimported_payload):
            raise GateBlocked("empty reimport did not complete synchronously")
        after = read_findings(client, headers, test_id)
    if [item.stage for item in statuses] != ["baseline_import", "empty_reimport"]:
        raise GateBlocked("execution state machine did not complete both HTTP operations")
    return {
        "scenario": SCENARIO, "run_id": run_id, "source": provenance,
        "fixture_sha256": fixture_hashes(), "service": SERVICE,
        "close_old_findings": True, "product_wide_closure": False, "test_id": test_id,
        "initial": [row.__dict__ for row in before], "final": [row.__dict__ for row in after],
        "http_statuses": [item.status for item in statuses],
        "operations_completed": [item.stage for item in statuses],
    }
