import json
from pathlib import Path

import pytest

from lab.sarif_identity import evaluate_sarif, sarif_fixture


def test_pair_only_changes_line():
    a, b = [json.loads(sarif_fixture(n)) for n in (10, 11)]
    b['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']['startLine'] = 10
    assert a == b
    assert Path('fixtures/sarif-14205-initial.json').read_bytes() == sarif_fixture(10)
    assert Path('fixtures/sarif-14205-moved.json').read_bytes() == sarif_fixture(11)


@pytest.mark.parametrize('field,value', [('id', 2), ('active', False),
                                        ('is_mitigated', True), ('duplicate', True)])
def test_oracle_rejects_identity_or_lifecycle_change(field, value):
    row = dict(id=1, test=1, unique_id_from_tool='synthetic', active=True,
               is_mitigated=False, duplicate=False)
    evaluate_sarif([row], [dict(row)])
    with pytest.raises(AssertionError):
        evaluate_sarif([row], [dict(row, **{field: value})])
