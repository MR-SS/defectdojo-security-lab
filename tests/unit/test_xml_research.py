"""Offline evidence/fixture oracle, not a live API or normalization test."""
import hashlib
import json
from pathlib import Path


def test_xml_evidence_and_bounds():
    data = json.loads(Path('docs/xml-14752-results.json').read_text())
    rows = {r['case']: r for r in data['results']}
    expected = {
        'baseline': (1, None), 'unexpected-root': (0, None),
        'empty': (None, 500), 'truncated': (None, 500),
        'encoding': (None, 500), 'missing-attribute': (None, 500),
        'partial': (None, 500), 'entity': (None, 400), 'invalid-integer': (None, 400),
    }
    assert len(rows) == len(data['results']) == len(expected)
    assert set(rows) == set(expected)
    for name, (count, status) in expected.items():
        raw = Path(f'fixtures/xml-14752/{name}.xml').read_bytes()
        assert len(raw) <= 2048
        assert b'SYSTEM' not in raw and b'PUBLIC' not in raw
        assert raw.count(b'<') <= 12
        assert rows[name]['sha256'] == hashlib.sha256(raw).hexdigest()
        assert rows[name]['returned'] == count
        assert rows[name]['handler_status'] == status
    assert rows['partial']['constructed'] == 1
    assert data['configuration']['forbid_entities'] is True
    assert data['configuration']['forbid_external'] is True
