import json
from pathlib import Path


def test_derived_pair_is_synthetic_and_preserves_distribution():
    from lab.semgrep_derived import derived_pair
    blobs = derived_pair()
    a, b = [json.loads(blob)['runs'][0]['results'] for blob in blobs]
    assert len(a) == 143 and len(b) == 142
    assert b == a[:1] + a[2:]
    assert len({r['ruleId'] for r in a}) == 30
    assert len({r['message']['text'] for r in a}) == 143
    assert all(r['fingerprints'] == {'matchBasedId/v1': 'requires login'} for r in a)
    assert all('snippet' not in str(r) and 'http' not in str(r) for r in a)
    assert derived_pair() == blobs
    for phase, blob in zip(('initial', 'changed'), blobs, strict=True):
        assert Path(f'fixtures/semgrep-derived-{phase}.json').read_bytes() == blob
