"""Offline tests for the XML lifecycle gate and execution state machine."""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from lab.xml_lifecycle import (
    BASELINE,
    EMPTY,
    INVALID,
    SCENARIO,
    GateBlocked,
    execute_empty_control,
    fixture_hashes,
    require_gate,
)

SOURCE = "/home/sajjad/.hermes/cache/scratch/ddslab-upstream/3.5.101"
SOURCE_PROVENANCE = {"commit": "32aea6841a019b050737c8874b939b236095333e", "files": {}}
BASE_ENV = {
    "DDSLAB_RUN_INTEGRATION": "1",
    "DDSLAB_APPROVE_SCENARIO": SCENARIO,
    "DDSLAB_SOURCE_CHECKOUT": SOURCE,
    "DDSLAB_PRODUCT_TYPE_ID": "3",
    "DDSLAB_API_BASE_URL": "http://ddslab.test",
    "DDSLAB_API_TOKEN": "redacted-test-token",
}


def test_fixture_checksums_and_bounds() -> None:
    assert fixture_hashes() == {
        str(BASELINE): "c9c7d6474447d2ac91637bed36b649306606858119d3655818ba385175faf202",
        str(EMPTY): "ccacac3cd5303b2f3c2bb26ee0838b3aa409173a473fd700062b1cd787d5d1b8",
        str(INVALID): "a8c11b30f8edcd179d79ff4a399fff445a5681ef58c66dcfb95998ae056395c6",
    }
    assert all(
        path.stat().st_size <= 4096 for path in (BASELINE, EMPTY, INVALID)
    )


def test_missing_approval_blocks_before_client_creation() -> None:
    with pytest.raises(GateBlocked):
        require_gate({**BASE_ENV, "DDSLAB_APPROVE_SCENARIO": ""})


def test_wrong_product_type_blocks() -> None:
    with pytest.raises(GateBlocked):
        require_gate({**BASE_ENV, "DDSLAB_PRODUCT_TYPE_ID": "2"})


def test_missing_source_blocks() -> None:
    env = {key: value for key, value in BASE_ENV.items() if key != "DDSLAB_SOURCE_CHECKOUT"}
    with pytest.raises(GateBlocked):
        require_gate(env)


def test_runtime_mismatch_blocks() -> None:
    with pytest.raises(GateBlocked):
        require_gate(
            BASE_ENV,
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: (_ for _ in ()).throw(GateBlocked("runtime mismatch")),
        )


def _client(transport: httpx.MockTransport, **kwargs: Any) -> httpx.Client:
    return httpx.Client(transport=transport, **kwargs)


def test_successful_two_operation_state_machine() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.method == "GET" and request.url.path == "/api/v2/":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/api/v2/product_types/3/":
            return httpx.Response(200, json={"id": 3})
        if request.method == "POST" and request.url.path == "/api/v2/products/":
            return httpx.Response(201, json={"id": 41})
        if request.method == "POST" and request.url.path == "/api/v2/engagements/":
            return httpx.Response(201, json={"id": 42})
        if request.method == "POST" and request.url.path == "/api/v2/import-scan/":
            return httpx.Response(201, json={"test": 43, "deduplication_complete": True})
        if request.method == "POST" and request.url.path == "/api/v2/reimport-scan/":
            return httpx.Response(201, json={"deduplication_complete": True})
        if request.method == "GET" and request.url.path == "/api/v2/findings/":
            rows = [
                {"id": i, "test": 43, "unique_id_from_tool": chr(96 + i),
                 "active": True, "is_mitigated": False}
                for i in range(1, 4)
            ]
            return httpx.Response(200, json={"results": rows, "next": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    result = execute_empty_control(
        env=BASE_ENV,
        client_factory=lambda **kwargs: _client(transport, **kwargs),
        source_verifier=lambda _: SOURCE_PROVENANCE,
        runtime_verifier=lambda _: None,
    )
    assert result["operations_completed"] == ["baseline_import", "empty_reimport"]
    assert result["http_statuses"] == [201, 201]
    assert calls.count("/api/v2/import-scan/") == 1
    assert calls.count("/api/v2/reimport-scan/") == 1


def test_import_failure_stops_without_reimport() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v2/":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/api/v2/product_types/3/":
            return httpx.Response(200, json={"id": 3})
        if request.url.path == "/api/v2/products/":
            return httpx.Response(201, json={"id": 41})
        if request.url.path == "/api/v2/engagements/":
            return httpx.Response(201, json={"id": 42})
        if request.url.path == "/api/v2/import-scan/":
            return httpx.Response(400, json={"detail": "rejected"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_empty_control(
            env=BASE_ENV,
        client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
    assert "/api/v2/reimport-scan/" not in calls


def test_incomplete_synchronous_import_blocks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/api/v2/product_types/3/":
            return httpx.Response(200, json={"id": 3})
        if request.url.path == "/api/v2/products/":
            return httpx.Response(201, json={"id": 41})
        if request.url.path == "/api/v2/engagements/":
            return httpx.Response(201, json={"id": 42})
        if request.url.path == "/api/v2/import-scan/":
            return httpx.Response(201, json={"test": 43, "status": "queued"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    with pytest.raises(GateBlocked):
        execute_empty_control(
            env=BASE_ENV,
        client_factory=lambda **kwargs: _client(transport, **kwargs),
            source_verifier=lambda _: SOURCE_PROVENANCE,
            runtime_verifier=lambda _: None,
        )
