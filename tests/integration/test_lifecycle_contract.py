"""Integration baseline that is inert without explicit local opt-in."""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

from lab.lifecycle import (
    assert_lifecycle_baseline,
    get_findings_for_test,
    integration_is_enabled,
    load_lifecycle_fixture,
    validate_contract_dry_run,
)

pytestmark = pytest.mark.integration


def test_lifecycle_contract_dry_run_has_no_writes():
    result = validate_contract_dry_run()
    assert result["finding_count"] == 3
    assert result["writes_performed"] is False


@pytest.mark.skipif(
    not integration_is_enabled(),
    reason="set DDSLAB_RUN_INTEGRATION=1 for live API mutation",
)
def test_live_generic_findings_import_reimport_baseline():
    """Run only under a separately approved explicit environment opt-in."""
    base_url = os.environ["DDSLAB_API_BASE_URL"]
    token = os.environ["DDSLAB_API_TOKEN"]
    product_type = int(os.environ["DDSLAB_PRODUCT_TYPE_ID"])
    scenario = f"ddslab-lifecycle-{uuid.uuid4().hex[:12]}"
    headers = {"Authorization": f"Token {token}"}
    fixture = load_lifecycle_fixture()

    with httpx.Client(base_url=base_url, timeout=60, trust_env=False) as client:
        product = client.post(
            "/api/v2/products/",
            headers=headers,
            json={
                "name": scenario,
                "description": "Synthetic local lifecycle regression scenario.",
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
        uploaded = {"file": ("generic-findings.json", fixture, "application/json")}
        imported = client.post(
            "/api/v2/import-scan/",
            headers=headers,
            data={
                "scan_type": "Generic Findings Import",
                "engagement": str(engagement.json()["id"]),
                "minimum_severity": "Info",
                "deduplication_execution_mode": "sync",
                "test_title": scenario,
                "close_old_findings": "false",
            },
            files=uploaded,
        )
        assert imported.status_code == 201
        test_id = imported.json()["test"]
        before = get_findings_for_test(client, headers, test_id)
        reimported = client.post(
            "/api/v2/reimport-scan/",
            headers=headers,
            data={
                "scan_type": "Generic Findings Import",
                "test": str(test_id),
                "minimum_severity": "Info",
                "deduplication_execution_mode": "sync",
                "close_old_findings": "false",
                "do_not_reactivate": "false",
            },
            files=uploaded,
        )
        assert reimported.status_code == 201
        after = get_findings_for_test(client, headers, test_id)

    assert_lifecycle_baseline(before, after)
