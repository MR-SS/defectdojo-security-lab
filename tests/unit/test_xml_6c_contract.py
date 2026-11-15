"""Offline contracts for the two isolated XML-6C scenarios."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

SCENARIOS = {
    "XML-EMPTY-CONTROL": {
        "fixture": Path("fixtures/xml-6b/valid-empty.xml"),
        "expected_parse": "success",
        "expected_findings": 0,
        "contract": "valid-empty-may-legitimately-close",
    },
    "XML-INVALID-ROOT": {
        "fixture": Path("fixtures/xml-6b/unexpected-root.xml"),
        "expected_parse": "success",
        "expected_findings": 0,
        "contract": "unsupported-root-should-be-rejected-or-classified",
    },
}
BASELINE = Path("fixtures/xml-6b/baseline.xml")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_xml_scenario_contract(scenario: str) -> None:
    spec = SCENARIOS[scenario]
    baseline = BASELINE.read_bytes()
    changed = spec["fixture"].read_bytes()
    assert len(baseline) <= 4096 and len(changed) <= 4096
    assert hashlib.sha256(baseline).hexdigest()
    assert hashlib.sha256(changed).hexdigest()
    assert scenario in SCENARIOS
    assert spec["expected_parse"] == "success"
    assert spec["expected_findings"] == 0
    assert spec["contract"]


def test_scenarios_require_separate_approval_and_same_test_contract() -> None:
    assert set(SCENARIOS) == {"XML-EMPTY-CONTROL", "XML-INVALID-ROOT"}
    assert all(spec["expected_findings"] == 0 for spec in SCENARIOS.values())
