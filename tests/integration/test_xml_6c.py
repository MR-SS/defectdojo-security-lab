"""Opt-in integration entrypoints for the two XML lifecycle scenarios."""
from __future__ import annotations

import os

import pytest

from lab.xml_lifecycle import (
    EMPTY_CONTROL,
    SCENARIO_INVALID_ROOT,
    execute_empty_control,
    execute_invalid_root,
)

pytestmark = pytest.mark.integration


def _approved(name: str) -> bool:
    return os.getenv("DDSLAB_RUN_INTEGRATION") == "1" and os.getenv(
        "DDSLAB_APPROVE_SCENARIO"
    ) == name


@pytest.mark.skipif(not _approved(EMPTY_CONTROL), reason="requires XML-EMPTY-CONTROL approval")
def test_xml_empty_control_live_entrypoint() -> None:
    """Run exactly one approved scenario; failures are never converted to PASS."""
    result = execute_empty_control()
    assert result["operations_completed"] == ["baseline_import", "empty_reimport"]
    assert result["http_statuses"] == [201, 201]
    assert result["scenario"] == EMPTY_CONTROL


@pytest.mark.skipif(
    not _approved(SCENARIO_INVALID_ROOT), reason="requires XML-INVALID-ROOT approval"
)
def test_xml_invalid_root_live_entrypoint() -> None:
    """Oracle records actual behavior; it never forces a PASS."""
    result = execute_invalid_root()
    assert result["operations_completed"] == ["baseline_import", "invalid_root_reimport"]
    assert result["http_statuses"][0] == 201
    assert result["scenario"] == SCENARIO_INVALID_ROOT
    assert result["verdict"] in {
        "application-behaved-correctly",
        "rejected-but-findings-changed",
        "integrity-defect-exhibited",
        "accepted-without-closure",
    }
