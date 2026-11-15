"""Offline negative tests for the XML-INVALID-ROOT scenario harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from lab.xml_lifecycle import (
    BASELINE,
    INVALID_ROOT,
    SCENARIO_INVALID_ROOT,
    GateBlocked,
    execute_invalid_root,
    fixture_hashes,
    require_gate,
    verify_fixtures,
    verify_parser_outputs,
)
from lab.xml_lifecycle import (
    SCENARIO_INVALID_ROOT as SCENARIO_INVALID,
)

SOURCE = "/home/sajjad/.hermes/cache/scratch/ddslab-source-clean/3.5.101"
SOURCE_PROVENANCE: dict[str, Any] = {
    "commit": "32aea6841a019b050737c8874b939b236095333e",
    "files": {},
}
BASE_ENV = {
    "DDSLAB_RUN_INTEGRATION": "1",
    "DDSLAB_APPROVE_SCENARIO": SCENARIO_INVALID,
    "DDSLAB_SOURCE_CHECKOUT": SOURCE,
    "DDSLAB_PRODUCT_TYPE_ID": "3",
    "DDSLAB_API_BASE_URL": "http://ddslab.test",
    "DDSLAB_API_TOKEN": "redacted-test-token",
}
STAGES = ["baseline_import", "invalid_root_reimport"]


def test_fixture_checksums_and_bounds() -> None:
    assert fixture_hashes()[str(BASELINE)] == (
        "c9c7d6474447d2ac91637bed36b649306606858119d3655818ba385175faf202"
    )
    assert fixture_hashes()[str(INVALID_ROOT)] == (
        "a8c11b30f8edcd179d79ff4a399fff445a5681ef58c66dcfb95998ae056395c6"
    )
    assert all(Path(p).stat().st_size <= 4096 for p in fixture_hashes())


def test_parser_output_verifier_requires_exact_counts() -> None:
    with pytest.raises(GateBlocked):
        verify_parser_outputs({"baseline.xml": 3, "unexpected-root.xml": 1})
    with pytest.raises(GateBlocked):
        verify_parser_outputs({"baseline.xml": 2, "unexpected-root.xml": 0})
    verify_parser_outputs({"baseline.xml": 3, "unexpected-root.xml": 0})


def test_missing_or_wrong_approval_blocks() -> None:
    for approval in ("", "XML-EMPTY-CONTROL", "xml-invalid-root", None):
        env = {**BASE_ENV, "DDSLAB_APPROVE_SCENARIO": approval or ""}
        with pytest.raises(GateBlocked):
            require_gate(
                env,
                SCENARIO_INVALID_ROOT,
                source_verifier=lambda _: SOURCE_PROVENANCE,
                runtime_verifier=lambda _: None,
            )


def test_wrong_product_type_blocks() -> None:
    with pytest.raises(GateBlocked):
        require_gate(
            {**BASE_ENV, "DDSLAB_PRODUCT_TYPE_ID": "2"},
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )


def test_failed_source_provenance_blocks() -> None:
    def fail(_: Path) -> dict[str, Any]:
        raise GateBlocked("source provenance failed")

    with pytest.raises(GateBlocked):
        require_gate(BASE_ENV, source_verifier=fail, runtime_verifier=lambda _: None)


def test_failed_runtime_correspondence_blocks() -> None:
    def fail(_: dict[str, Any]) -> None:
        raise GateBlocked("runtime mismatch")

    with pytest.raises(GateBlocked):
        require_gate(
            BASE_ENV,
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=fail,
        )


def _client(transport: httpx.MockTransport, **kwargs: Any) -> httpx.Client:
    return httpx.Client(transport=transport, **kwargs)


def _base_handler(calls: list[str]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "GET" and request.url.path == "/api/v2/":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/api/v2/product_types/3/":
            return httpx.Response(200, json={"id": 3})
        if request.method == "POST" and request.url.path == "/api/v2/products/":
            return httpx.Response(201, json={"id": 51})
        if request.method == "POST" and request.url.path == "/api/v2/engagements/":
            return httpx.Response(201, json={"id": 52})
        if request.method == "POST" and request.url.path == "/api/v2/import-scan/":
            return httpx.Response(201, json={"test": 53, "deduplication_complete": True})
        return None

    return handler


def _rows(test_id: int, active: bool) -> list[dict[str, Any]]:
    return [
        {
            "id": i,
            "test": test_id,
            "unique_id_from_tool": None,
            "active": active,
            "is_mitigated": not active,
        }
        for i in (601, 602, 603)
    ]


def _run(
    handler: Any,
    *,
    env: dict[str, str] | None = None,
    parser_outputs: dict[str, int] | None = None,
) -> dict[str, Any]:
    transport = httpx.MockTransport(handler)
    return execute_invalid_root(
        env=env or BASE_ENV,
        client_factory=lambda **kwargs: _client(transport, **kwargs),
        source_verifier=lambda _: SOURCE_PROVENANCE,
        runtime_verifier=lambda _: None,
        parser_verifier=(lambda outputs: None)
        if parser_outputs is None
        else (lambda outputs: verify_parser_outputs(outputs)),
        live_parser_probe=lambda: None,
    )


def test_correct_invalid_root_rejection_passes() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(400, json={"error": "unsupported root"})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            return httpx.Response(200, json={"results": _rows(53, active=True), "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    result = _run(handler)
    assert result["http_statuses"] == [201, 400]
    assert result["verdict"] == "application-behaved-correctly"
    assert result["transition_counts"] == {
        "created": 0,
        "closed": 0,
        "unchanged": 3,
        "reactivated": 0,
    }
    assert calls.count("POST /api/v2/import-scan/") == 1
    assert calls.count("POST /api/v2/reimport-scan/") == 1


def test_unexpected_acceptance_and_closure_recorded_not_forced() -> None:
    calls: list[str] = []
    findings_calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(201, json={"deduplication_complete": True})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            findings_calls["count"] += 1
            active = findings_calls["count"] == 1
            return httpx.Response(200, json={"results": _rows(53, active=active), "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    result = _run(handler)
    assert result["http_statuses"] == [201, 201]
    assert result["verdict"] == "integrity-defect-exhibited"
    assert result["transition_counts"]["closed"] == 3
    # no assertion failure: the oracle records actual behavior


def test_initial_import_failure_stops_without_reimport() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v2/":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/api/v2/product_types/3/":
            return httpx.Response(200, json={"id": 3})
        if request.method == "POST" and request.url.path == "/api/v2/products/":
            return httpx.Response(201, json={"id": 51})
        if request.method == "POST" and request.url.path == "/api/v2/engagements/":
            return httpx.Response(201, json={"id": 52})
        if request.method == "POST" and request.url.path == "/api/v2/import-scan/":
            return httpx.Response(500, json={"error": "boom"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
    assert not any("reimport-scan" in call for call in calls)


def test_incomplete_synchronous_reimport_stops() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(201, json={"status": "queued"})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            return httpx.Response(200, json={"results": _rows(53, active=True), "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
    assert calls.count("POST /api/v2/reimport-scan/") == 1


def test_wrong_finding_count_or_ownership_blocks() -> None:
    calls: list[str] = []
    findings_calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(400, json={"error": "unsupported root"})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            findings_calls["count"] += 1
            rows = _rows(53, active=True)
            if findings_calls["count"] == 1:
                rows.append(
                    {
                        "id": 604,
                        "test": 53,
                        "unique_id_from_tool": None,
                        "active": True,
                        "is_mitigated": False,
                    }
                )
            return httpx.Response(200, json={"results": rows, "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )


def test_duplicate_finding_ids_block() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(400, json={"error": "unsupported root"})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            row = {
                "id": 601,
                "test": 53,
                "unique_id_from_tool": None,
                "active": True,
                "is_mitigated": False,
            }
            return httpx.Response(200, json={"results": [row] * 3, "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )


def test_no_retry_after_partial_mutation() -> None:
    calls: list[str] = []
    boom_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            boom_count["n"] += 1
            return httpx.Response(500, json={"error": "server error"})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            return httpx.Response(200, json={"results": _rows(53, active=True), "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
    assert boom_count["n"] == 1
    assert calls.count("POST /api/v2/import-scan/") == 1


def test_false_pass_impossible_without_both_operations() -> None:
    """A run that somehow skips reimport cannot produce a PASS-shaped result."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        base = _base_handler(calls)(request)
        if base is not None:
            return base
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            return httpx.Response(200, json={"results": _rows(53, active=True), "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises((GateBlocked, AssertionError)):
        execute_invalid_root(
            env=BASE_ENV,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )


def test_verify_fixtures_still_guards_all_three() -> None:
    verify_fixtures()  # must not raise; includes unexpected-root.xml digest


def test_empty_control_approval_cannot_authorize_invalid_root() -> None:
    env = {**BASE_ENV, "DDSLAB_APPROVE_SCENARIO": "XML-EMPTY-CONTROL"}
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"error": "must not be called"})
    )
    with pytest.raises(GateBlocked):
        execute_invalid_root(
            env=env,
            client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
