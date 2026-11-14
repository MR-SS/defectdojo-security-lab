"""Deterministic SARIF collision/removal contracts. No runtime access."""
import copy
import json
from pathlib import Path

from lab.sarif_identity import sarif_fixture

CASES = ('S2', 'S3-A', 'S3-B')


def pair(case):
    if case not in CASES:
        raise ValueError('unknown SARIF case')
    payload = json.loads(sarif_fixture(10))
    template = payload['runs'][0]['results'][0]
    results = []
    for index in range(2 if case == 'S2' else 3):
        result = copy.deepcopy(template)
        result['ruleId'] = f'ddslab/rule-{index}'
        result['message']['text'] = f'Synthetic distinct vulnerability {index}'
        uid = 'collision' if case in ('S2', 'S3-B') and index < 2 else f'unique-{index}'
        result['partialFingerprints']['primaryLocationLineHash'] = uid
        results.append(result)
    payload['runs'][0]['results'] = results
    changed = copy.deepcopy(payload)
    if case != 'S2':
        del changed['runs'][0]['results'][1]
    def encode(value):
        return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    return encode(payload), encode(changed)


def load_pair(case):
    expected = pair(case)
    actual = tuple(Path(f'fixtures/sarif-{case}-{phase}.json').read_bytes()
                   for phase in ('initial', 'changed'))
    if actual != expected:
        raise ValueError('fixture drift')
    return actual


def evaluate(case, before, after):
    expected_count = 2 if case == 'S2' else 3
    assert len(before) == len(after) == expected_count
    old, new = ({r['id']: r for r in rows} for rows in (before, after))
    assert old.keys() == new.keys()
    assert len({r['vuln_id_from_tool'] for r in before}) == expected_count
    for fid, row in old.items():
        final = new[fid]
        assert row['active'] and not row['is_mitigated'] and not row['duplicate']
        for key in ('test', 'hash_code', 'vuln_id_from_tool', 'file_path', 'line'):
            assert final[key] == row[key]
        closed = case != 'S2' and row['vuln_id_from_tool'] == 'ddslab/rule-1'
        assert final['active'] is (not closed)
        assert final['is_mitigated'] is closed
        assert not final['duplicate']
    # UID persistence is evidence, not the key used to compare rows.
