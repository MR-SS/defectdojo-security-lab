import hashlib
import json

import pytest

from lab.evidence import sanitize
from lab.lifecycle import (
    FIXTURE_PATH,
    REMOVAL_FIXTURE_PATH,
    FindingState,
    assert_lifecycle_baseline,
    integration_is_enabled,
    load_lifecycle_fixture,
    load_removal_fixture,
    normalize_findings,
    validate_contract_dry_run,
)


def test_tracked_lifecycle_fixture_is_deterministic_and_valid():
    first = load_lifecycle_fixture()
    second = load_lifecycle_fixture()
    assert first == second
    assert len(json.loads(first)["findings"]) == 3
    assert hashlib.sha256(first).hexdigest()


def test_dry_run_contract_performs_no_database_writes():
    assert validate_contract_dry_run()["writes_performed"] is False


def test_normalize_and_compare_stable_lifecycle_states():
    states = normalize_findings(
        {
            "results": [
                {"id": 7, "unique_id_from_tool": "a", "active": True, "is_mitigated": False},
                {"id": 8, "unique_id_from_tool": "b", "active": True, "is_mitigated": False},
                {"id": 9, "unique_id_from_tool": "c", "active": True, "is_mitigated": False},
            ]
        }
    )
    assert_lifecycle_baseline(states, states)


def test_duplicate_or_lifecycle_change_is_rejected():
    before = tuple(FindingState(index, str(index), True, False) for index in range(1, 4))
    duplicate = (before[0], before[0], before[2])
    transitioned = (before[0], FindingState(2, "2", False, True), before[2])
    with pytest.raises(AssertionError, match="duplicate"):
        assert_lifecycle_baseline(before, duplicate)
    with pytest.raises(AssertionError, match="identities"):
        assert_lifecycle_baseline(before, transitioned)


def test_missing_or_ambiguous_api_responses_are_rejected():
    with pytest.raises(ValueError, match="lacks results"):
        normalize_findings({})
    with pytest.raises(ValueError, match="ambiguous"):
        normalize_findings({"results": [{"id": "not-an-id"}]})


def test_safe_evidence_redaction_and_opt_in_are_explicit(monkeypatch):
    assert sanitize({"authorization": "unsafe", "nested": {"token": "unsafe"}}) == {
        "authorization": "[REDACTED]",
        "nested": {"token": "[REDACTED]"},
    }
    monkeypatch.delenv("DDSLAB_RUN_INTEGRATION", raising=False)
    assert integration_is_enabled() is False
    monkeypatch.setenv("DDSLAB_RUN_INTEGRATION", "1")
    assert integration_is_enabled() is True


def test_fixture_path_is_tracked_fixture():
    assert FIXTURE_PATH.as_posix() == "fixtures/generic-findings-lifecycle-3.json"


def test_removal_fixture_retains_a_and_c_and_omits_b():
    payload = json.loads(load_removal_fixture())
    assert REMOVAL_FIXTURE_PATH.as_posix() == "fixtures/generic-findings-removal-ac.json"
    assert {item["unique_id_from_tool"] for item in payload["findings"]} == {
        "finding-0000",
        "finding-0002",
    }
