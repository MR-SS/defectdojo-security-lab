import copy
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize('handler', ['vulnerabilities', 'checks', 'secrets'])
def test_only_replicaset_suffix_changes(handler):
    from lab.trivy_identity import pair
    blobs = pair(handler)
    initial, changed = [json.loads(b) for b in blobs]
    expected = copy.deepcopy(initial)
    expected[0]['metadata']['labels']['trivy-operator.resource.name'] = 'alpha-7c8d9f6b5c'
    assert changed == expected
    assert initial[1] == changed[1]
    assert len(initial) == 2
    assert all(len(r['report'][handler]) == 1 for r in initial)
    for phase, blob in zip(('initial', 'changed'), blobs, strict=True):
        assert Path(f'fixtures/trivy-{handler}-{phase}.json').read_bytes() == blob
