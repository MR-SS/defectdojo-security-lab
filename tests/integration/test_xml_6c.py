"""Milestone 6C lifecycle entrypoints, intentionally disabled for live execution.

The two names are separate approval domains. This module only validates that the
scenario gate is explicit; it never creates products, imports reports, or calls
an API during Milestone 6C.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lab.lifecycle import integration_is_enabled

SCENARIOS = {
    "XML-EMPTY-CONTROL": Path("fixtures/xml-6b/valid-empty.xml"),
    "XML-INVALID-ROOT": Path("fixtures/xml-6b/unexpected-root.xml"),
}
BASELINE = Path("fixtures/xml-6b/baseline.xml")

pytestmark = pytest.mark.integration


def scenario_approval(name: str) -> bool:
    """Require global opt-in and an exact, separate scenario approval."""
    return integration_is_enabled() and os.getenv("DDSLAB_APPROVE_SCENARIO") == name


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_scenario_isolated_and_bounded(name: str) -> None:
    changed = SCENARIOS[name].read_bytes()
    assert changed
    assert len(BASELINE.read_bytes()) <= 4096
    assert len(changed) <= 4096
    approval = os.getenv("DDSLAB_APPROVE_SCENARIO")
    assert approval not in SCENARIOS or approval == name


def test_xml_empty_control_entrypoint_is_not_enabled() -> None:
    assert not scenario_approval("XML-EMPTY-CONTROL")


def test_xml_invalid_root_entrypoint_is_not_enabled() -> None:
    assert not scenario_approval("XML-INVALID-ROOT")
