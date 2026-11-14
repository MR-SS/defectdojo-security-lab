"""Separate opt-in mutation tests for close_old_findings endpoint semantics."""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

from lab.lifecycle import (
    get_findings_for_test,
    integration_is_enabled,
    load_lifecycle_fixture,
    load_removal_fixture,
)

pytestmark = pytest.mark.integration


def _enabled(name: str) -> bool:
    return integration_is_enabled() and os.getenv(name) == "1"


def _create_context(client: httpx.Client, headers: dict[str, str], product_type: int, label: str):
    scenario = f"ddslab-{label}-{uuid.uuid4().hex[:12]}"
    product = client.post(
        "/api/v2/products/",
        headers=headers,
        json={
            "name": scenario,
            "description": "Synthetic removal regression scenario.",
            "prod_type": product_type,
        },
    )
    assert product.status_code == 201
    engagement = client.post(
        "/api/v2/engagements/",
        headers=headers,
        json={
            "name": scenario,
            "product": product.json()["id"],
            "target_start": "2026-11-14",
            "target_end": "2026-11-15",
            "status": "In Progress",
            "engagement_type": "CI/CD",
        },
    )
    assert engagement.status_code == 201
    return scenario, engagement.json()["id"]


def _import(
    client: httpx.Client, headers: dict[str, str], engagement: int, title: str, fixture: bytes
) -> int:
    response = client.post(
        "/api/v2/import-scan/",
        headers=headers,
        data={
            "scan_type": "Generic Findings Import",
            "engagement": str(engagement),
            "minimum_severity": "Info",
            "deduplication_execution_mode": "sync",
            "test_title": title,
            "close_old_findings": "true",
        },
        files={"file": ("generic-findings.json", fixture, "application/json")},
    )
    assert response.status_code == 201
    return response.json()["test"]


@pytest.mark.skipif(
    not _enabled("DDSLAB_RUN_R1"),
    reason="requires explicit DDSLAB_RUN_INTEGRATION=1 and DDSLAB_RUN_R1=1",
)
def test_r1_same_test_reimport_only_closes_absent_finding():
    """R1: target-Test B is expected to close because reimport uses target-Test bookkeeping."""
    base_url = os.environ["DDSLAB_API_BASE_URL"]
    headers = {"Authorization": f"Token {os.environ['DDSLAB_API_TOKEN']}"}
    product_type = int(os.environ["DDSLAB_PRODUCT_TYPE_ID"])
    with httpx.Client(base_url=base_url, timeout=60, trust_env=False) as client:
        scenario, engagement = _create_context(client, headers, product_type, "r1")
        test_id = _import(client, headers, engagement, scenario, load_lifecycle_fixture())
        before = get_findings_for_test(client, headers, test_id)
        response = client.post(
            "/api/v2/reimport-scan/",
            headers=headers,
            data={
                "scan_type": "Generic Findings Import",
                "test": str(test_id),
                "minimum_severity": "Info",
                "deduplication_execution_mode": "sync",
                "close_old_findings": "true",
                "close_old_findings_product_scope": "false",
                "do_not_reactivate": "false",
            },
            files={
                "file": (
                    "generic-findings-ac.json",
                    load_removal_fixture(),
                    "application/json",
                )
            },
        )
        assert response.status_code == 201
        after = get_findings_for_test(client, headers, test_id)
    assert len(before) == 3
    assert {item.unique_id_from_tool for item in after} == {
        "finding-0000",
        "finding-0002",
        "finding-0001",
    }
    b = next(item for item in after if item.unique_id_from_tool == "finding-0001")
    assert b.active is False and b.is_mitigated is True


@pytest.mark.skipif(
    not _enabled("DDSLAB_RUN_I1"),
    reason="requires explicit DDSLAB_RUN_INTEGRATION=1 and DDSLAB_RUN_I1=1",
)
def test_i1_new_import_closes_absent_same_engagement_sibling_test_finding():
    """I1: fresh import T2 is expected to close T1-B in the same Engagement scope."""
    base_url = os.environ["DDSLAB_API_BASE_URL"]
    headers = {"Authorization": f"Token {os.environ['DDSLAB_API_TOKEN']}"}
    product_type = int(os.environ["DDSLAB_PRODUCT_TYPE_ID"])
    with httpx.Client(base_url=base_url, timeout=60, trust_env=False) as client:
        scenario, engagement = _create_context(client, headers, product_type, "i1")
        first_test = _import(
            client, headers, engagement, f"{scenario}-t1", load_lifecycle_fixture()
        )
        second_test = _import(client, headers, engagement, f"{scenario}-t2", load_removal_fixture())
        first_after = get_findings_for_test(client, headers, first_test)
        second_after = get_findings_for_test(client, headers, second_test)
    assert len(second_after) == 2
    b = next(item for item in first_after if item.unique_id_from_tool == "finding-0001")
    assert b.active is False and b.is_mitigated is True
