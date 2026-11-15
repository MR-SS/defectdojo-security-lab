"""Explicitly gated live XML-EMPTY-CONTROL entrypoint."""
from __future__ import annotations

import os

import pytest

from lab.xml_lifecycle import SCENARIO, execute_empty_control

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("DDSLAB_RUN_INTEGRATION") != "1"
    or os.getenv("DDSLAB_APPROVE_SCENARIO") != SCENARIO,
    reason="requires exact XML-EMPTY-CONTROL approval and integration opt-in",
)
def test_xml_empty_control_live_entrypoint() -> None:
    """Run exactly one approved scenario; failures are never converted to PASS."""
    result = execute_empty_control()
    assert result["operations_completed"] == ["baseline_import", "empty_reimport"]
    assert result["http_statuses"] == [201, 201]
    assert result["scenario"] == SCENARIO
