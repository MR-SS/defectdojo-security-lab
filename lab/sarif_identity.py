"""Minimal unique-fingerprint SARIF control for issue 14205 (not collision coverage)."""
import json


def sarif_fixture(line):
    if line not in (10, 11):
        raise ValueError('unsupported location')
    payload = {'version': '2.1.0', 'runs': [{
        'tool': {'driver': {'name': 'DDSLAB synthetic SARIF'}},
        'results': [{'ruleId': 'ddslab/rule', 'level': 'warning',
                     'message': {'text': 'Synthetic identity control'},
                     'partialFingerprints': {'primaryLocationLineHash': 'synthetic-stable'},
                     'locations': [{'physicalLocation': {
                         'artifactLocation': {'uri': 'src/synthetic.py'},
                         'region': {'startLine': line}}}]}]}]}
    return (json.dumps(payload, indent=2, sort_keys=True) + '\n').encode()


def evaluate_sarif(before, after):
    assert len(before) == len(after) == 1
    a, b = before[0], after[0]
    for key in ('id', 'test', 'unique_id_from_tool'):
        assert a[key] == b[key]
    for row in (a, b):
        assert row['active'] and not row['is_mitigated'] and not row['duplicate']
    # Persisted hash/location reconciliation is observed separately.
