import copy
import json

import pytest

from lab.sarif_regressions import CASES, evaluate, load_pair, pair


@pytest.mark.parametrize('case', CASES)
def test_fixtures(case):
    initial, changed = load_pair(case)
    assert (initial, changed) == pair(case)
    a, b = [json.loads(x)['runs'][0]['results'] for x in (initial, changed)]
    assert b == (a if case == 'S2' else [a[0], a[2]])
    assert len({r['ruleId'] for r in a}) == len(a)


@pytest.mark.parametrize('case', CASES)
def test_oracle(case):
    before = [dict(id=i, test=1, hash_code=str(i), vuln_id_from_tool=f'ddslab/rule-{i}',
                   file_path='synthetic.py', line=10, active=True,
                   is_mitigated=False, duplicate=False) for i in range(2 if case == 'S2' else 3)]
    after = copy.deepcopy(before)
    if case != 'S2':
        after[1].update(active=False, is_mitigated=True)
    evaluate(case, before, after)
    after[0]['active'] = False
    with pytest.raises(AssertionError):
        evaluate(case, before, after)
