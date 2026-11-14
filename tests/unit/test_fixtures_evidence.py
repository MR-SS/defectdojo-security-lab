import json
from datetime import UTC, datetime

import pytest

from lab.evidence import safe_run_id, sanitize, write_manifest
from lab.fixtures import generic_findings, json_fixture, nmap_xml, write_fixture
from lab.models import EvidenceManifest
from tests.unit.test_models import result


def test_generic_fixture_is_deterministic():
    assert generic_findings(3).content == generic_findings(3).content
    assert generic_findings(3).sha256 == generic_findings(3).sha256


def test_fixture_changes_when_identity_changes():
    assert generic_findings(1).sha256 != generic_findings(1, changed_identity=True).sha256


def test_zero_one_many_fixture_counts():
    for count in (0, 1, 3):
        payload = json.loads(generic_findings(count).content)
        assert len(payload["findings"]) == count


def test_nmap_fixture_is_well_formed_xml():
    fixture = nmap_xml(2)
    assert fixture.valid is True
    assert fixture.content.startswith(b"<?xml")
    assert fixture.content.count(b"<host>") == 2


def test_malformed_fixture_is_marked_invalid():
    assert nmap_xml(1, malformed=True).valid is False
    assert json_fixture("SARIF", 1, malformed=True).valid is False


def test_fixture_metadata_records_checksum(tmp_path):
    fixture = generic_findings(1)
    metadata = write_fixture(fixture, tmp_path)
    assert metadata["sha256"] == fixture.sha256
    metadata_json = json.loads((tmp_path / "generic-findings.metadata.json").read_text())
    assert metadata_json["generator_version"]


def test_safe_run_id_rejects_traversal():
    with pytest.raises(ValueError):
        safe_run_id("../escape")


def test_sanitizer_redacts_secret_fields():
    value = sanitize({"api_token": "secret", "nested": {"password": "pw", "count": 1}})
    assert value == {"api_token": "[REDACTED]", "nested": {"password": "[REDACTED]", "count": 1}}


def test_evidence_writer_never_overwrites(tmp_path):
    manifest = EvidenceManifest(
        run_id="run-1",
        scenario_id="offline.fixture",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        result=result(),
    )
    first = write_manifest(tmp_path, manifest)
    assert json.loads((first / "manifest.json").read_text())["run_id"] == "run-1"
    with pytest.raises(FileExistsError):
        write_manifest(tmp_path, manifest)


def test_evidence_writer_writes_sanitized_manifest(tmp_path):
    manifest = EvidenceManifest(
        run_id="run-2",
        scenario_id="offline.fixture",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        result=result(),
        parameters={"password": "do-not-write"},
    )
    destination = write_manifest(tmp_path, manifest)
    text = (destination / "manifest.json").read_text()
    assert "do-not-write" not in text
    assert "[REDACTED]" in text
