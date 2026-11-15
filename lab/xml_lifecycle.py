"""Approval-gated Burp Dastardly XML lifecycle runners."""
from __future__ import annotations

import base64
import hashlib
import json
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
INVALID = Path("fixtures/xml-6b/unexpected-root.xml")
SCENARIO = "XML-EMPTY-CONTROL"
SCENARIO_INVALID_ROOT = "XML-INVALID-ROOT"
EMPTY_CONTROL = SCENARIO
INVALID_ROOT = Path("fixtures/xml-6b/unexpected-root.xml")
SERVICE = "xml-6c-stable-service"
EXPECTED_FIXTURES = {
    BASELINE: "c9c7d6474447d2ac91637bed36b649306606858119d3655818ba385175faf202",
    EMPTY: "ccacac3cd5303b2f3c2bb26ee0838b3aa409173a473fd700062b1cd787d5d1b8",
    INVALID: "a8c11b30f8edcd179d79ff4a399fff445a5681ef58c66dcfb95998ae056395c6",
}
EXPECTED_PARSER_OUTPUTS = {"baseline.xml": 3, "unexpected-root.xml": 0}
PARSER_FILES = (
    "dojo/tools/burp_dastardly/parser.py",
    "dojo/importers/default_importer.py",
    "dojo/importers/default_reimporter.py",
    "dojo/importers/base_importer.py",
    "dojo/api_v2/serializers.py",
)
PARSER_PROBE_CODE = (
    "import io,base64,json,sys\n"
    "from dojo.models import Test\n"
    "from dojo.tools.burp_dastardly.parser import BurpDastardlyParser\n"
    "out={name: len(BurpDastardlyParser().get_findings("
    "io.BytesIO(base64.b64decode(b64)), Test()))"
    " for name, b64 in json.load(sys.stdin).items()}\n"
    "print('COUNTS:'+json.dumps(out))\n"
)


@dataclass(frozen=True)
class RunResult:
    stage: str
    status: int


class GateBlocked(RuntimeError):
    """Raised before any mutating HTTP request is permitted."""


def fixture_hashes() -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in EXPECTED_FIXTURES}


def verify_fixtures() -> None:
    expected = {str(path): digest for path, digest in EXPECTED_FIXTURES.items()}
    if fixture_hashes() != expected:
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


def run_parser_probe() -> dict[str, int]:
    """Parser-only preflight inside the running container; no importer calls."""
    payload = {
        "baseline.xml": base64.b64encode(BASELINE.read_bytes()).decode(),
        "unexpected-root.xml": base64.b64encode(INVALID.read_bytes()).decode(),
    }
    result = subprocess.run(
        [
            "docker", "exec", "-i", "ddslab-uwsgi-1",
            "python", "manage.py", "shell", "-c", PARSER_PROBE_CODE,
        ],
        input=json.dumps(payload), capture_output=True, text=True, timeout=35, check=False,
    )
    if result.returncode or "COUNTS:" not in result.stdout:
        raise GateBlocked("parser output preflight failed")
    return json.loads(result.stdout.split("COUNTS:")[-1])


def verify_parser_outputs(outputs: dict[str, int]) -> None:
    """Baseline must yield three findings; the unsupported root must yield zero."""
    if outputs != EXPECTED_PARSER_OUTPUTS:
        raise GateBlocked(f"parser cardinality mismatch: {outputs}")


def approval_enabled(env: dict[str, str], scenario: str = SCENARIO) -> bool:
    return env.get("DDSLAB_RUN_INTEGRATION") == "1" and env.get(
        "DDSLAB_APPROVE_SCENARIO"
    ) == scenario


def require_gate(
    env: dict[str, str],
    scenario: str = SCENARIO,
    *,
    source_verifier: Callable[[Path], dict[str, Any]] = verify_source_checkout,
    runtime_verifier: Callable[[dict[str, Any]], None] = verify_runtime_correspondence,
) -> dict[str, Any]:
    if not approval_enabled(env, scenario):
        raise GateBlocked(f"missing exact integration opt-in or {scenario} approval")
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


def transition_counts(
    before: tuple[FindingState, ...], after: tuple[FindingState, ...]
) -> dict[str, int]:
    before_map = {row.finding_id: row for row in before}
    after_map = {row.finding_id: row for row in after}
    created = sum(1 for fid in after_map if fid not in before_map)
    reactivated = sum(
        1 for fid, row in after_map.items()
        if fid in before_map and not before_map[fid].active and row.active
    )
    closed = sum(
        1 for fid, row in after_map.items()
        if fid in before_map and before_map[fid].active and not row.active
    )
    unchanged = sum(
        1 for fid, row in after_map.items()
        if fid in before_map
        and before_map[fid].active == row.active
        and before_map[fid].is_mitigated == row.is_mitigated
    )
    return {
        "created": created, "closed": closed, "unchanged": unchanged,
        "reactivated": reactivated,
    }


def _create_isolated_context(
    client: httpx.Client, headers: dict[str, str], run_id: str
) -> int:
    product = client.post(
        "/api/v2/products/",
        headers=headers,
        json={
            "name": run_id,
            "description": "Synthetic XML lifecycle scenario.",
            "prod_type": 3,
        },
    )
    if product.status_code != 201:
        raise GateBlocked(f"Product creation returned HTTP {product.status_code}")
    engagement = client.post(
        "/api/v2/engagements/",
        headers=headers,
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
    return int(_json(engagement)["id"])


def _import_baseline(
    client: httpx.Client, headers: dict[str, str], engagement_id: int, run_id: str
) -> int:
    imported = client.post(
        "/api/v2/import-scan/",
        headers=headers,
        data={
            "scan_type": "Burp Dastardly Scan", "engagement": str(engagement_id),
            "minimum_severity": "Info", "deduplication_execution_mode": "sync",
            "test_title": run_id, "close_old_findings": "false", "service": SERVICE,
        },
        files={"file": ("baseline.xml", BASELINE.read_bytes(), "application/xml")},
    )
    if imported.status_code != 201 or not _sync_complete(_json(imported)):
        raise GateBlocked("baseline import did not complete synchronously")
    return int(_json(imported)["test"])


def _verify_readiness(client: httpx.Client, headers: dict[str, str]) -> None:
    readiness = client.get("/api/v2/", headers=headers)
    if readiness.status_code != 200:
        raise GateBlocked(f"API readiness returned HTTP {readiness.status_code}")
    product_type = client.get("/api/v2/product_types/3/", headers=headers)
    if product_type.status_code != 200 or _json(product_type).get("id") != 3:
        raise GateBlocked("Product Type 3 isolation could not be verified")


def execute_empty_control(
    *,
    env: dict[str, str] | None = None,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
    source_verifier: Callable[[Path], dict[str, Any]] = verify_source_checkout,
    runtime_verifier: Callable[[dict[str, Any]], None] = verify_runtime_correspondence,
) -> dict[str, Any]:
    """Perform exactly one approved baseline import and one approved empty reimport."""
    values = dict(os.environ if env is None else env)
    provenance = require_gate(values, source_verifier=source_verifier,
                              runtime_verifier=runtime_verifier)
    headers = {"Authorization": f"Token {values['DDSLAB_API_TOKEN']}"}
    run_id = f"xml-empty-control-{uuid.uuid4().hex[:12]}"
    statuses: list[RunResult] = []
    with client_factory(
        base_url=values["DDSLAB_API_BASE_URL"], headers=headers, timeout=60, trust_env=False
    ) as client:
        _verify_readiness(client, headers)
        engagement_id = _create_isolated_context(client, headers, run_id)
        test_id = _import_baseline(client, headers, engagement_id, run_id)
        statuses.append(RunResult("baseline_import", 201))
        before = read_findings(client, headers, test_id)
        reimported = client.post(
            "/api/v2/reimport-scan/",
            headers=headers,
            data={
                "scan_type": "Burp Dastardly Scan", "test": str(test_id),
                "minimum_severity": "Info", "deduplication_execution_mode": "sync",
                "close_old_findings": "true", "close_old_findings_product_scope": "false",
                "do_not_reactivate": "false", "service": SERVICE,
            },
            files={"file": ("valid-empty.xml", EMPTY.read_bytes(), "application/xml")},
        )
        statuses.append(RunResult("empty_reimport", reimported.status_code))
        if reimported.status_code != 201 or not _sync_complete(_json(reimported)):
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


def execute_invalid_root(
    *,
    env: dict[str, str] | None = None,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
    source_verifier: Callable[[Path], dict[str, Any]] = verify_source_checkout,
    runtime_verifier: Callable[[dict[str, Any]], None] = verify_runtime_correspondence,
    parser_verifier: Callable[[dict[str, int]], None] = verify_parser_outputs,
    live_parser_probe: Callable[[], dict[str, int] | None] | None = None,
) -> dict[str, Any]:
    """One approved baseline import plus one invalid-root reimport.

    The oracle records observed behavior; it never forces a PASS.
    """
    values = dict(os.environ if env is None else env)
    provenance = require_gate(
        values, SCENARIO_INVALID_ROOT, source_verifier=source_verifier,
        runtime_verifier=runtime_verifier,
    )
    if live_parser_probe is not None:
        outputs = live_parser_probe()
        if outputs is not None:
            parser_verifier(outputs)
    headers = {"Authorization": f"Token {values['DDSLAB_API_TOKEN']}"}
    run_id = f"xml-invalid-root-{uuid.uuid4().hex[:12]}"
    statuses: list[RunResult] = []
    with client_factory(
        base_url=values["DDSLAB_API_BASE_URL"], headers=headers, timeout=60, trust_env=False
    ) as client:
        _verify_readiness(client, headers)
        engagement_id = _create_isolated_context(client, headers, run_id)
        test_id = _import_baseline(client, headers, engagement_id, run_id)
        statuses.append(RunResult("baseline_import", 201))
        before = read_findings(client, headers, test_id)
        reimported = client.post(
            "/api/v2/reimport-scan/",
            headers=headers,
            data={
                "scan_type": "Burp Dastardly Scan", "test": str(test_id),
                "minimum_severity": "Info", "deduplication_execution_mode": "sync",
                "close_old_findings": "true", "close_old_findings_product_scope": "false",
                "do_not_reactivate": "false", "service": SERVICE,
            },
            files={"file": ("unexpected-root.xml", INVALID.read_bytes(), "application/xml")},
        )
        statuses.append(RunResult("invalid_root_reimport", reimported.status_code))
        if reimported.status_code == 400:
            outcome = "rejected_with_validation_error"
        elif reimported.status_code == 201:
            if not _sync_complete(_json(reimported)):
                raise GateBlocked("invalid-root reimport was accepted but not synchronous")
            outcome = "accepted_as_empty_scan"
        else:
            raise GateBlocked(
                f"invalid-root reimport returned HTTP {reimported.status_code}"
            )
        after = read_findings(client, headers, test_id)
    if [item.stage for item in statuses] != ["baseline_import", "invalid_root_reimport"]:
        raise GateBlocked("execution state machine did not complete both HTTP operations")
    counts = transition_counts(before, after)
    ids_preserved = {row.finding_id for row in before} == {row.finding_id for row in after}
    all_closed = ids_preserved and all(not row.active and row.is_mitigated for row in after)
    if outcome == "rejected_with_validation_error":
        verdict = (
            "application-behaved-correctly" if counts["closed"] == 0 and ids_preserved
            else "rejected-but-findings-changed"
        )
    else:
        verdict = "integrity-defect-exhibited" if all_closed else "accepted-without-closure"
    return {
        "scenario": SCENARIO_INVALID_ROOT, "run_id": run_id, "source": provenance,
        "fixture_sha256": fixture_hashes(), "service": SERVICE,
        "close_old_findings": True, "product_wide_closure": False, "test_id": test_id,
        "initial": [row.__dict__ for row in before], "final": [row.__dict__ for row in after],
        "http_statuses": [item.status for item in statuses],
        "operations_completed": [item.stage for item in statuses],
        "outcome": outcome, "verdict": verdict, "transition_counts": counts,
        "parser_output": dict(EXPECTED_PARSER_OUTPUTS),
        "behavior_note": "behavior recorded from observed API responses; no oracle was forced",
    }
